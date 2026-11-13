"""Agente Juiz. Dono: Rafael.
Contrato (TRD §3): recebe tudo dos outros agentes; saída {verdict, risk_score, explanation_ptbr, reasons[]}.
Regras de decisão (TRD §4), todas em código:
  - qualquer violação de política        -> BLOCK
  - endereço em blocklist                -> BLOCK
  - approve ilimitado + contrato < 7 dias + não verificado -> BLOCK
  - risk_score >= 40                     -> WARN; senão ALLOW
  - simulação falhou (App Flow)          -> WARN
  - função não identificada              -> WARN (não dá para explicar o efeito: nunca PERMITIR às cegas)
O LLM redige a explicação e pode SUBIR o risco (até MAX_EXTRA_RISK); nunca baixa o piso.
Ele usa o que sobrou do orçamento de tempo de LLM da análise (TRD §7); sem tempo, vale o texto das regras."""
import re
import time
import uuid

from agents import llm
from agents.policy import contract_age_violations
from agents.prompts import JUDGE_SYSTEM, JudgeOut, judge_user_prompt
from tools.hashing import intent_hash, report_hash

ORDER = {"ALLOW": 0, "WARN": 1, "BLOCK": 2}
WARN_THRESHOLD = 40
RISK_FLOOR = {"ALLOW": 0, "WARN": WARN_THRESHOLD, "BLOCK": 70}   # score coerente com o selo exibido
STRONG_SIGNALS = {"UNLIMITED_APPROVAL", "CONTRACT_NEW", "UNVERIFIED"}
SCORE_REASON = "Sinais de risco somam"
TAIL = {"BLOCK": "Não assine.", "WARN": "Revise com cuidado antes de assinar.", "ALLOW": "Pode assinar."}

_RECOMMENDATION = re.compile(
    r"(\s*\**(n[ãa]o assine|revise[^.!?]{0,40}antes de assinar|pode assinar)\**[.!]*)+\s*$", re.I)
_ADDRESS = re.compile(r"0x[a-fA-F0-9]{40}\b")
# Texto que manda ou autoriza assinar. Vindo do LLM em um veredito que não é PERMITIR, é contradição.
_REASSURING = re.compile(
    r"(?<!não )(?<!nao )\b(assine|assinar agora|pode assinar|pode prosseguir|pode confirmar|pode aprovar|"
    r"seguro assinar|é segur[oa]|e segur[oa]|sem risco|confie|aprove)\b", re.I)


def rule_verdict(threat: dict, pol: dict) -> tuple[str, list[str]]:
    """Piso do veredito. Só código: nada aqui depende de LLM."""
    codes = {s["code"] for s in threat["signals"]}
    reasons: list[str] = []
    verdict = "ALLOW"

    def at_least(v: str, why: str):
        nonlocal verdict
        reasons.append(why)
        if ORDER[v] > ORDER[verdict]:
            verdict = v

    for viol in pol["violations"]:
        at_least("BLOCK", viol)
    if "BLOCKLISTED" in codes:
        at_least("BLOCK", "Endereço está em lista de golpes conhecidos.")
    if STRONG_SIGNALS <= codes:
        at_least("BLOCK", "Permissão ilimitada para contrato novo e não verificado (padrão de phishing de aprovação).")
    if "SIMULATION_FAILED" in codes:   # estado de erro do App Flow: simulação falhou -> ALERTAR
        at_least("WARN", "Não foi possível simular a transação — não assine às cegas.")
    if "UNKNOWN_FUNCTION" in codes:    # piso próprio: vale mesmo se o score ficar abaixo do limiar
        at_least("WARN", "Não foi possível identificar o que a transação faz — não assine às cegas.")
    if "PROMPT_INJECTION" in codes:
        reasons.append("A mensagem que originou a transação tem sinais de manipulação (prompt injection).")
    r = threat["risk_score"]
    if r >= WARN_THRESHOLD:
        at_least("WARN", f"{SCORE_REASON} {r}/100.")
    return verdict, reasons


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
    tx, d, t = state["tx"], state["decoded"], state["threat"]
    patterns = state.get("rag_docs") or []
    errors: list[str] = []

    # Política completa = regras do nó Política + idade mínima do contrato (dado coletado pelo Ameaças)
    violations = state["policy_result"]["violations"] + contract_age_violations(
        state.get("policy") or {}, state.get("contracts") or {})
    p = {"allowed": not violations, "violations": violations}

    verdict, reasons = rule_verdict(t, p)
    risk = max(t["risk_score"], RISK_FLOOR[verdict])

    explanation, used_llm = None, False
    started = time.monotonic()
    out, err = llm.chat_structured(
        JUDGE_SYSTEM, judge_user_prompt(d, t, p, verdict, risk, reasons, patterns, tx.get("context")), JudgeOut,
        timeout=llm.BUDGET_S - state.get("llm_seconds", 0.0))
    llm_seconds = time.monotonic() - started
    if err:
        errors.append(f"judge: {err}")
    if out:
        if out.extra_risk:
            risk = min(100, risk + out.extra_risk)
            reasons += [r for r in out.extra_reasons if not _REASSURING.search(r)]
            if risk >= WARN_THRESHOLD and verdict == "ALLOW":
                verdict = "WARN"
                reasons.append(f"{SCORE_REASON} {risk}/100 após a análise do Juiz.")
        explanation = finalize_explanation(out.explanation_ptbr, verdict)
        if explanation is None:
            errors.append("judge: explicação do LLM descartada por contradizer o veredito")
        used_llm = explanation is not None or bool(out.extra_risk)   # texto aceito ou risco elevado pelo LLM
    if explanation is None:
        explanation = template_explanation(verdict, d, reasons, patterns)

    report = {"decoded": d, "threat": t, "policy": p, "verdict": verdict, "risk_score": risk, "reasons": reasons}
    result = {
        "analysis_id": str(uuid.uuid4()),
        "verdict": verdict,
        "risk_score": risk,
        "explanation_ptbr": explanation,
        "reasons": reasons,
        "decoded": d,
        "threat": t,
        "policy": p,
        "intent_hash": intent_hash(tx.get("chain_id", 1), tx["from"], tx["to"], tx.get("value") or "0", tx.get("data") or "0x"),
        "report_hash": report_hash(report),
        "llm_used": used_llm or any(u for _, u in state.get("llm_calls", [])),
    }
    return {"verdict": result, "errors": errors, "llm_seconds": llm_seconds}
