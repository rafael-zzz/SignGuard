"""Agente Juiz + Explicador. Dono: Rafael.
Contrato (TRD §3): recebe tudo dos outros agentes; saída {verdict, risk_score, explanation_ptbr, reasons[]}.

"O probabilístico só filtra, o determinístico decide" (docs/07-alinhamento-jurado.md):
  judge_node    decide. Só código, sem LLM e sem rede. BLOQUEAR vem exclusivamente de regra:
      - qualquer violação de política                            -> BLOCK
      - endereço em blocklist                                    -> BLOCK
      - approve ilimitado + contrato < 7 dias + não verificado   -> BLOCK
    Tudo o mais tem teto de ALERTAR:
      - regra de política não conferida (token sem preço x limite em USD) -> WARN
      - simulação falhou / função não identificada (fora do escopo)       -> WARN (fail-closed)
      - sinais do classificador (PROMPT_INJECTION, INTENT_MISMATCH, CLASSIFIER_UNAVAILABLE) -> WARN
      - risk_score >= 40                                                   -> WARN; senão ALLOW
  explain_node  roda DEPOIS do veredito. O LLM reescreve o texto e nada mais: veredito, risco,
    motivos e report_hash já estão fechados. Texto que contradiz o veredito é descartado; sem LLM
    (ou acima de LLM_TIMEOUT), vale o template e o veredito é o mesmo."""
import re
import time
import uuid

from agents import llm
from agents.policy import contract_age_violations
from agents.prompts import EXPLAIN_SYSTEM, ExplainOut, explain_user_prompt
from agents.threat import CLASSIFIER_CODES
from tools.hashing import intent_hash, report_hash

ORDER = {"ALLOW": 0, "WARN": 1, "BLOCK": 2}
WARN_THRESHOLD = 40
RISK_FLOOR = {"ALLOW": 0, "WARN": WARN_THRESHOLD, "BLOCK": 70}   # score coerente com o selo exibido
STRONG_SIGNALS = {"UNLIMITED_APPROVAL", "CONTRACT_NEW", "UNVERIFIED"}
assert not STRONG_SIGNALS & CLASSIFIER_CODES   # nenhum sinal probabilístico entra em regra de BLOQUEAR
SCORE_REASON = "Sinais de risco somam"
TAIL = {"BLOCK": "Não assine.", "WARN": "Revise com cuidado antes de assinar.", "ALLOW": "Pode assinar."}

_RECOMMENDATION = re.compile(
    r"(\s*\**(n[ãa]o assine|revise[^.!?]{0,40}antes de assinar|pode assinar)\**[.!]*)+\s*$", re.I)
_ADDRESS = re.compile(r"0x[a-fA-F0-9]{40}\b")
# Texto que manda ou autoriza assinar. Vindo do LLM em um veredito que não é PERMITIR, é contradição.
_REASSURING = re.compile(
    r"(?<!não )(?<!nao )\b(assine|assinar agora|pode assinar|pode prosseguir|pode confirmar|pode aprovar|"
    r"seguro assinar|é segur[oa]|e segur[oa]|sem risco|confie|aprove)\b", re.I)


def decide(threat: dict, pol: dict) -> tuple[str, list[dict]]:
    """O veredito. Função pura de (sinais, política): mesmo input -> mesmo output, sem LLM e sem rede.
    Cada motivo sai com a origem: "rule" (determinístico) e/ou "classifier" (probabilístico, com a
    probabilidade). Motivo de classificador nunca passa de WARN."""
    by_code = {s["code"]: s for s in threat["signals"]}
    codes = set(by_code)
    details: list[dict] = []
    verdict = "ALLOW"

    def at_least(v: str, why: str, code: str | None = None):
        nonlocal verdict
        sig = by_code.get(code) or {}
        sources = list(sig.get("sources") or ["rule"])
        if v == "BLOCK" and sources != ["rule"]:   # invariante: BLOQUEAR só por regra em código
            v = "WARN"
        details.append({"text": why, "sources": sources, "probability": sig.get("probability")})
        if ORDER[v] > ORDER[verdict]:
            verdict = v

    for viol in pol["violations"]:
        at_least("BLOCK", viol)
    for warn in pol.get("warnings") or []:   # regra que não pôde ser conferida: nunca PERMITIR às cegas
        at_least("WARN", warn)
    if "BLOCKLISTED" in codes:
        at_least("BLOCK", "Endereço está em lista de golpes conhecidos.")
    if STRONG_SIGNALS <= codes:
        at_least("BLOCK", "Permissão ilimitada para contrato novo e não verificado (padrão de phishing de aprovação).")
    if "SIMULATION_FAILED" in codes:   # estado de erro do App Flow: simulação falhou -> ALERTAR
        at_least("WARN", "Não foi possível simular a transação — não assine às cegas.")
    if "UNKNOWN_FUNCTION" in codes:    # fora do escopo garantido: piso próprio, vale mesmo com score baixo
        at_least("WARN", "Não foi possível identificar o que a transação faz — não assine às cegas.")
    # Camada probabilística (regex OU Jev): piso ALERTAR, teto ALERTAR
    if "PROMPT_INJECTION" in codes:
        at_least("WARN", "A mensagem que originou a transação tem sinais de manipulação (prompt injection).",
                 "PROMPT_INJECTION")
    if "INTENT_MISMATCH" in codes:
        at_least("WARN", "A transação faz mais do que a mensagem pediu (valor, permissão ou destino diferente).",
                 "INTENT_MISMATCH")
    if "CLASSIFIER_UNAVAILABLE" in codes:
        at_least("WARN", "O classificador de contexto não respondeu e a transação veio de um agente — "
                         "precisa de revisão humana.", "CLASSIFIER_UNAVAILABLE")
    r = threat["risk_score"]
    if r >= WARN_THRESHOLD:            # score sozinho alerta; nunca bloqueia
        at_least("WARN", f"{SCORE_REASON} {r}/100.")
    return verdict, details


def rule_verdict(threat: dict, pol: dict) -> tuple[str, list[str]]:
    verdict, details = decide(threat, pol)
    return verdict, [x["text"] for x in details]


def short_addresses(text: str) -> str:
    """Na explicação os endereços aparecem como 0x1234…abcd (Design Brief); o endereço completo fica em reasons/decoded."""
    return _ADDRESS.sub(lambda m: f"{m[0][:6]}…{m[0][-4:]}", text)


def template_explanation(verdict: str, decoded: dict, reasons: list[str], patterns: list[dict]) -> str:
    """Explicação no modo regras (sem LLM)."""
    main = [r for r in reasons if not r.startswith(SCORE_REASON)] or reasons   # o score já aparece no selo
    parts = [decoded["summary_ptbr"], *main[:2]]
    if verdict != "ALLOW" and patterns:
        parts.append(f"Padrão conhecido: {patterns[0]['title']}.")
    parts.append(TAIL[verdict])
    return short_addresses(" ".join(p.strip() for p in parts if p).replace("  ", " "))


def finalize_explanation(text: str, verdict: str) -> str | None:
    """Aceita o texto do LLM só se ele não contradiz o veredito. A recomendação final é sempre a do código."""
    if verdict != "ALLOW" and _REASSURING.search(text):
        return None
    body = _RECOMMENDATION.sub("", text).strip()
    if not body:
        return None
    if body[-1] not in ".!?…":
        body += "."
    return short_addresses(f"{body} {TAIL[verdict]}")


def judge_node(state: dict) -> dict:
    """Decide. Nenhuma chamada de modelo aqui: o veredito sai fechado, com hash, antes de qualquer LLM."""
    tx, d, t = state["tx"], state["decoded"], state["threat"]
    patterns = state.get("rag_docs") or []

    # Política completa = regras do nó Política + idade mínima do contrato (dado coletado pelo Ameaças)
    violations = state["policy_result"]["violations"] + contract_age_violations(
        state.get("policy") or {}, state.get("contracts") or {})
    p = {"allowed": not violations, "violations": violations,
         "warnings": state["policy_result"].get("warnings") or []}

    verdict, details = decide(t, p)
    reasons = [x["text"] for x in details]
    risk = max(t["risk_score"], RISK_FLOOR[verdict])

    # O relatório atestado inclui threat.classifier: versão do Jev, probabilidades e limiares (docs/07 §6.4)
    report = {"decoded": d, "threat": t, "policy": p, "verdict": verdict, "risk_score": risk, "reasons": reasons}
    result = {
        "analysis_id": str(uuid.uuid4()),
        "verdict": verdict,
        "risk_score": risk,
        "explanation_ptbr": template_explanation(verdict, d, reasons, patterns),
        "reasons": reasons,
        "reason_details": details,
        "decoded": d,
        "threat": t,
        "policy": p,
        "intent_hash": intent_hash(tx.get("chain_id", 1), tx["from"], tx["to"], tx.get("value") or "0", tx.get("data") or "0x"),
        "report_hash": report_hash(report),
        "llm_used": False,
        "timings_ms": {},
    }
    return {"verdict": result}


def explain_node(state: dict) -> dict:
    """Fora do caminho da decisão. Só troca `explanation_ptbr` (e marca `llm_used`)."""
    v, tx = state["verdict"], state["tx"]
    out, err = llm.chat_structured(
        EXPLAIN_SYSTEM,
        explain_user_prompt(v["decoded"], v["threat"], v["policy"], v["verdict"], v["risk_score"], v["reasons"],
                            state.get("rag_docs") or [], tx.get("context")),
        ExplainOut, timeout=llm.BUDGET_S)
    errors = [f"explain: {err}"] if err else []
    if not out:
        return {"errors": errors}
    text = finalize_explanation(out.explanation_ptbr, v["verdict"])
    if text is None:
        return {"errors": errors + ["explain: explicação do LLM descartada por contradizer o veredito"]}
    return {"verdict": {**v, "explanation_ptbr": text, "llm_used": True}, "errors": errors}
