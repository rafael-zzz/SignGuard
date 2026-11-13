"""Agente de Ameaças. Dono: Rafael (tools: Dávila).
Contrato (TRD §3): entrada `tx`, `decoded`; ferramentas `contract_info`, `check_blocklist`
(db.check_blocklist) e `search_patterns`; saída {signals[], risk_score, evidence[]} (+ patterns do RAG).
Tudo aqui é código: sinais objetivos com peso. `evidence` registra o que foi consultado,
inclusive o que estava indisponível. Pesos ajustáveis em WEIGHTS."""
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor

from agents.policy import fmt_age
from api import db
from tools.decode import fmt_br, known_contract_name
from tools.etherscan import contract_info
from tools.rag import search_patterns

WEIGHTS = {
    "BLOCKLISTED": 100,
    "UNLIMITED_APPROVAL": 35,
    "CONTRACT_NEW": 25,
    "UNVERIFIED": 20,
    "SIMULATION_FAILED": 40,
    "UNKNOWN_FUNCTION": 40,   # não dá para explicar o que faz -> nunca PERMITIR às cegas (PRD §1, blind signing)
    "PROMPT_INJECTION": 40,   # sozinho já tira o PERMITIR: agente manipulado não assina (PRD, história 4)
    "HIGH_VALUE": 15,
}
NEW_CONTRACT_DAYS = 7         # TRD §4: "contrato < 7 dias"
HIGH_VALUE_USD = 1000

# Roda sobre o texto normalizado (minúsculo, sem acento).
INJECTION_HINTS = re.compile(
    r"(ignor\w*|desconsider\w*|esquec\w*|disregard|forget|override)\b.{0,40}"
    r"(instruc|instruct|regra|rule|anterior|previous|prior|acima|above|politica|policy)"
    r"|system prompt|prompt de sistema|modo desenvolvedor|developer mode|jailbreak"
    r"|voce agora e|you are now|a partir de agora voce|from now on you"
    r"|(transfira|transferir|envie|enviar|mande|send|transfer)\b.{0,30}(todo|toda|tudo|saldo|all|entire|everything|balance)"
    r"|(mude|altere|troque|change)\b.{0,20}(veredito|verdict)"
    r"|(responda|retorne|devolva|return|answer)\b.{0,20}(allow|permitir)"
    r"|(sem|nao|without|don't|do not)\b.{0,25}(consultar|chamar|verificar|checar|check|call)\b.{0,15}signguard"
    r"|</?\s*(untrusted|system)\b",
)


def _normalize(text: str) -> str:
    """Minúsculo, sem acento e sem caracteres invisíveis (zero-width etc.) usados para driblar o filtro."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c) and unicodedata.category(c) != "Cf")
    return re.sub(r"\s+", " ", text).lower()


def detect_injection(context: str | None) -> str | None:
    """Devolve o trecho suspeito (normalizado) ou None."""
    if not context:
        return None
    m = INJECTION_HINTS.search(_normalize(context))
    return m.group(0)[:80] if m else None


def _short(a: str) -> str:
    return f"{a[:6]}…{a[-4:]}"


def threat_node(state: dict) -> dict:
    tx, d = state["tx"], state["decoded"]
    offline = state.get("offline") or {}
    sim = state.get("simulation") or {}
    found: dict[str, list[str]] = {}      # código -> evidências (um sinal por código)
    evidence: list[str] = []              # o que o agente viu, inclusive checagens sem achado
    errors: list[str] = []

    def add(code: str, ev: str):
        found.setdefault(code, []).append(ev)

    # 1) Blocklist: contrato chamado e todo endereço que aparece na transação (quem recebe a permissão
    #    ou os fundos, a origem de um transferFrom, os tokens do caminho de um swap)
    addrs = sorted({a.lower() for a in (tx["to"], d.get("spender"), d.get("recipient"), d.get("token"),
                                        *(state.get("involved") or [])) if a})
    try:
        hits = db.check_blocklist(addrs)
        evidence.append(f"blocklist: {len(addrs)} endereço(s) consultado(s), {len(hits)} ocorrência(s)")
        for hit in hits:
            add("BLOCKLISTED", f"{hit['address']} — {hit['label']} (fonte: {hit['source']})")
    except Exception as e:  # noqa: BLE001
        evidence.append("blocklist: indisponível")
        errors.append(f"threat: blocklist indisponível ({type(e).__name__})")

    # 2) Sinais que saem direto da decodificação/simulação
    if d["action"] == "approve" and d["is_unlimited"]:
        add("UNLIMITED_APPROVAL", f"approve ilimitado de {d.get('token_symbol')} para {d.get('spender')}")
    if d["action"] == "unknown" and state.get("to_contract"):
        add("UNKNOWN_FUNCTION", f"ETH enviado direto ao contrato {state['to_contract']}, que executa código próprio ao receber")
    elif d["action"] == "unknown":
        add("UNKNOWN_FUNCTION", f"função {d.get('function')} não reconhecida")
    if (d.get("amount_usd") or 0) >= HIGH_VALUE_USD:
        add("HIGH_VALUE", f"valor estimado US$ {fmt_br(d['amount_usd'], 2)}")

    if d.get("simulation_ok") is False:
        add("SIMULATION_FAILED", f"a simulação reverteu ({sim.get('detail') or 'sem detalhe'})")
    elif d.get("simulation_ok") is None and sim.get("attempted"):
        add("SIMULATION_FAILED", f"não foi possível simular ({sim.get('detail') or 'sem detalhe'})")
    elif d.get("simulation_ok") is None:
        evidence.append("simulação: indisponível (OFFLINE ou sem RPC configurado)")
    else:
        source = sim.get("balance_changes_source")
        evidence.append("simulação: executa sem reverter" + (f" (mudanças de saldo: {source})" if source else ""))

    # 3) Reputação dos contratos envolvidos: o contrato chamado, quem recebe a permissão e, em um
    #    swap, os tokens do caminho. Contratos conhecidos também são consultados: a idade mínima da
    #    política vale para todos. As consultas rodam em paralelo (orçamento de 4 s do TRD §7).
    targets: list[str] = []
    if d["action"] == "approve" and d.get("spender"):
        targets.append(d["spender"].lower())
    if d["action"] != "native_transfer":
        targets.append(tx["to"].lower())
    if d["action"] == "swap":
        targets += [a for a in state.get("involved") or [] if a != (d.get("recipient") or "").lower()]
    targets = list(dict.fromkeys(targets))

    def lookup(addr: str) -> dict:
        try:
            return contract_info(addr, tx.get("chain_id", 1), offline)
        except Exception as e:  # noqa: BLE001
            return {"source": "indisponível", "error": type(e).__name__}

    with ThreadPoolExecutor(max_workers=max(1, min(4, len(targets)))) as pool:
        infos = list(pool.map(lookup, targets))

    contracts: dict[str, dict] = {}
    for addr, info in zip(targets, infos):
        name = known_contract_name(addr)
        label = f"contrato {_short(addr)}" + (f" ({name})" if name else "")
        if info.get("error"):
            errors.append(f"threat: contract_info falhou ({info['error']})")
        age, verified, is_contract = info.get("age_days"), info.get("verified"), info.get("is_contract")
        if age is None and verified is None and is_contract is not True:
            evidence.append(f"{label}: reputação indisponível (Etherscan fora ou sem chave)")
            continue
        if is_contract is False:
            evidence.append(f"{label}: é uma carteira comum, não um contrato (fonte: {info.get('source', '?')})")
            continue
        contracts[addr] = info
        facts = []
        if age is not None:
            facts.append(f"criado há {fmt_age(age)}")
            if age < NEW_CONTRACT_DAYS:
                add("CONTRACT_NEW", f"contrato {addr} criado há {fmt_age(age)}")
        else:
            facts.append("idade não confirmada")
        if verified is not None:
            facts.append("código verificado" if verified else "código não verificado")
            if verified is False:
                add("UNVERIFIED", f"código-fonte de {addr} não verificado no Etherscan")
        evidence.append(f"{label}: {', '.join(facts)} (fonte: {info.get('source', '?')})")

    # 4) Mensagem que acompanha a transação: dado não confiável, analisado por regex (sem LLM)
    snippet = detect_injection(tx.get("context"))
    if snippet:
        add("PROMPT_INJECTION", f"o contexto contém instruções típicas de manipulação de agente: “{snippet}”")

    # 5) RAG: padrões de golpe parecidos com o que foi encontrado
    try:
        docs = search_patterns([*found, d["action"], tx.get("context") or ""])
    except Exception as e:  # noqa: BLE001
        docs = []
        errors.append(f"threat: RAG indisponível ({type(e).__name__})")
    if docs:
        evidence.append("padrões conhecidos (RAG): " + "; ".join(p["title"] for p in docs))

    signals = [{"code": c, "weight": WEIGHTS[c], "evidence": "; ".join(ev)} for c, ev in found.items()]
    risk = min(100, sum(s["weight"] for s in signals))
    return {
        "threat": {"signals": signals, "risk_score": risk, "patterns": [p["title"] for p in docs], "evidence": evidence},
        "contracts": contracts,
        "rag_docs": docs,
        "errors": errors,
    }
