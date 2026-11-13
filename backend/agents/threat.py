"""Agente de Ameaças. Dono: Rafael (tools: Dávila).
Contrato (TRD §3): entrada `tx`, `decoded`; ferramentas `contract_info`, `check_blocklist`
(db.check_blocklist), `search_patterns` e o classificador Jev; saída {signals[], risk_score, evidence[],
classifier} (+ patterns do RAG).
Os sinais on-chain são código (REGRA). O texto do contexto é classificado pelo Jev (probabilidade
calibrada) e por regex, em OU; o limiar fixo em tools/jev.py transforma probabilidade em sinal.
Sinal de classificador só tira o PERMITIR: o teto dele é ALERTAR (agents/judge.py). Ver docs/07 §4.
`evidence` registra o que foi consultado, inclusive o que estava indisponível. Pesos em WEIGHTS."""
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor

from agents.policy import fmt_age
from api import db
from tools.decode import fmt_br, known_contract_name
from tools import jev
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
    "INTENT_MISMATCH": 40,    # a transação faz mais do que a mensagem pediu (Jev): tira o PERMITIR
    "CLASSIFIER_UNAVAILABLE": 40,   # tx de agente com contexto e classificador fora: fail-closed
    "HIGH_VALUE": 15,
}
# Sinais que vêm (ou podem vir) da camada probabilística. Nenhum deles participa de regra de BLOQUEAR.
CLASSIFIER_CODES = frozenset({"PROMPT_INJECTION", "INTENT_MISMATCH", "CLASSIFIER_UNAVAILABLE"})
NEW_CONTRACT_DAYS = 7         # TRD §4: "contrato < 7 dias"
HIGH_VALUE_USD = 1000

# Roda sobre o texto normalizado (minúsculo, sem acento).
INJECTION_HINTS = re.compile(
    r"(ignor\w*|desconsider\w*|esquec\w*|disregard|forget|override)\b.{0,40}"
    r"(instruc|instruct|regra|rule|anterior|previous|prior|acima|above|politica|policy)"
    r"|system prompt|prompt de sistema|modo desenvolvedor|developer mode|jailbreak"
    r"|voce agora e|you are now|a partir de agora voce|from now on you"
    r"|(transfira|transferir|envie|enviar|mande|send|transfer)\b.{0,30}\b(todo|toda|tudo|saldo|all|entire|everything|balance)\b"
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


def _p(x: float) -> str:
    return f"{x:.2f}".replace(".", ",")


def classify_context(tx: dict, acao_real: str, offline: dict) -> tuple[dict | None, list[dict], list[str], int | None]:
    """Camada probabilística (docs/07 §4.3): regex OU Jev -> sinais, por limiar fixo em código.
    Devolve (classifier para o relatório, sinais, evidências, latência do Jev em ms)."""
    context = tx.get("context")
    if not context:
        return None, [], [], None
    signals: list[dict] = []
    evidence: list[str] = []

    def signal(code: str, ev: list[str], sources: list[str], probability: float | None = None):
        signals.append({"code": code, "weight": WEIGHTS[code], "evidence": "; ".join(ev),
                        "sources": sources, "probability": probability})

    snippet = detect_injection(context)
    out = jev.classify(context, acao_real, offline)
    classifier = {"provider": jev.backend() or "typesafe", "model": jev.model_name(), "status": "off", "calibrated": True,
                  "thresholds": {"injection": jev.INJECTION_T, "intent": jev.INTENT_T},
                  "injection_p": None, "injection_scores": None, "intent": None, "intent_confidence": None,
                  "intent_probabilities": None, "error": None}
    latency = None
    if out is None:
        evidence.append("classificador: desligado (sem chave ou OFFLINE); contexto checado só por regex")
    elif "error" in out:
        latency = out.get("latency_ms")
        classifier.update(status="error", error=out["error"])
        evidence.append(f"classificador: indisponível ({out['error']}); contexto checado só por regex")
    else:
        latency = out.get("latency_ms")
        classifier.update(status="ok", provider=out["provider"], calibrated=out["calibrated"],
                          model=out["model"], injection_p=out["injection_p"],
                          injection_scores=out["injection_scores"] or None, intent=out["intent"],
                          intent_confidence=out["intent_confidence"], intent_probabilities=out["intent_probabilities"])
        evidence.append(f"classificador Jev ({out['model']}, via {out['provider']}): injeção p={_p(out['injection_p'])} "
                        f"(limiar {_p(jev.INJECTION_T)}); intenção {out['intent']} "
                        f"com confiança {_p(out['intent_confidence'])} (limiar {_p(jev.INTENT_T)})")

    ok = classifier["status"] == "ok"
    inj_ev, inj_src = [], []
    if snippet:
        inj_ev.append(f"o contexto contém instruções típicas de manipulação de agente: “{snippet}”")
        inj_src.append("rule")
    if ok and classifier["injection_p"] >= jev.INJECTION_T:
        scores = classifier["injection_scores"] or {}
        which = max(scores, key=scores.get) if scores else None
        label = {"override": "manda ignorar ou mudar regras", "impersonation": "se passa pelo sistema ou diz que já foi aprovado",
                 "bypass": "pede para pular a verificação", "drain": "pede para mover todo o saldo"}.get(which)
        inj_ev.append(f"classificador: probabilidade de injeção {_p(classifier['injection_p'])} ≥ {_p(jev.INJECTION_T)}"
                      + (f" ({label})" if label else ""))
        inj_src.append("classifier")
    if inj_src:
        signal("PROMPT_INJECTION", inj_ev, inj_src, classifier["injection_p"] if ok else None)
    if ok and classifier["intent"] == "divergente" and classifier["intent_confidence"] >= jev.INTENT_T:
        signal("INTENT_MISMATCH",
               [f"classificador: a ação real diverge do que a mensagem pede "
                f"(confiança {_p(classifier['intent_confidence'])} ≥ {_p(jev.INTENT_T)})"],
               ["classifier"], classifier["intent_confidence"])
    if classifier["status"] == "error" and tx.get("source") == "agent":
        signal("CLASSIFIER_UNAVAILABLE",
               ["transação de agente com contexto e o classificador não respondeu: sem a segunda checagem, não há PERMITIR"],
               ["rule"])
    return classifier, signals, evidence, latency


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

    # 4) Mensagem que acompanha a transação: dado não confiável. Regex OU Jev, por limiar fixo.
    #    O que sai daqui só pode tirar o PERMITIR (teto ALERTAR), nunca BLOQUEAR.
    facts = "; ".join(ev for code in ("UNLIMITED_APPROVAL", "CONTRACT_NEW", "UNVERIFIED", "HIGH_VALUE")
                      for ev in found.get(code, []))
    acao_real = d["summary_ptbr"] + (f" ({facts})" if facts else "")
    classifier, ctx_signals, ctx_evidence, jev_ms = classify_context(tx, acao_real, offline)
    evidence += ctx_evidence

    # 5) RAG: padrões de golpe parecidos com o que foi encontrado
    try:
        docs = search_patterns([*found, *(s["code"] for s in ctx_signals), d["action"], tx.get("context") or ""])
    except Exception as e:  # noqa: BLE001
        docs = []
        errors.append(f"threat: RAG indisponível ({type(e).__name__})")
    if docs:
        evidence.append("padrões conhecidos (RAG): " + "; ".join(p["title"] for p in docs))

    signals = [{"code": c, "weight": WEIGHTS[c], "evidence": "; ".join(ev), "sources": ["rule"], "probability": None}
               for c, ev in found.items()] + ctx_signals
    risk = min(100, sum(s["weight"] for s in signals))
    return {
        "threat": {"signals": signals, "risk_score": risk, "patterns": [p["title"] for p in docs],
                   "evidence": evidence, "classifier": classifier},
        "contracts": contracts,
        "rag_docs": docs,
        "errors": errors,
        "timings": {"jev": jev_ms} if jev_ms is not None else {},
    }
