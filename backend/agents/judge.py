"""Agente Juiz. Dono: Rafael.
Piso de decisão em código; o LLM só escreve a explicação e pode SUBIR o risco."""
import json
import uuid

from agents import llm
from agents.prompts import JUDGE_SYSTEM, untrusted
from tools.hashing import intent_hash, report_hash

ORDER = {"ALLOW": 0, "WARN": 1, "BLOCK": 2}


def rule_verdict(threat: dict, pol: dict) -> tuple[str, list[str]]:
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
    if {"UNLIMITED_APPROVAL", "CONTRACT_NEW", "UNVERIFIED"} <= codes:
        at_least("BLOCK", "Permissão ilimitada para contrato novo e não verificado (padrão de phishing de aprovação).")
    if "SIMULATION_FAILED" in codes:
        at_least("WARN", "Não foi possível simular a transação com sucesso.")
    r = threat["risk_score"]
    if r >= 70:
        at_least("BLOCK", f"Risco alto ({r}/100).")
    elif r >= 40:
        at_least("WARN", f"Risco moderado ({r}/100).")
    return verdict, reasons


def _from_score(score: int) -> str:
    return "BLOCK" if score >= 70 else "WARN" if score >= 40 else "ALLOW"


def template_explanation(verdict: str, decoded: dict, reasons: list[str]) -> str:
    tail = {"BLOCK": "Não assine.", "WARN": "Revise com cuidado antes de assinar.", "ALLOW": "Pode assinar."}[verdict]
    why = " ".join(reasons[:2])
    return f"{decoded['summary_ptbr']} {why} {tail}".replace("  ", " ").strip()


def judge_node(state: dict) -> dict:
    tx, d, t, p = state["tx"], state["decoded"], state["threat"], state["policy_result"]
    verdict, reasons = rule_verdict(t, p)
    risk = t["risk_score"]
    if verdict == "BLOCK":
        risk = max(risk, 70)

    explanation = template_explanation(verdict, d, reasons)
    used_llm = False
    out = llm.chat_json(
        JUDGE_SYSTEM,
        json.dumps({"decodificador": d, "ameacas": t, "politica": p,
                    "veredito_minimo": verdict, "risco_minimo": risk, "motivos": reasons}, ensure_ascii=False)
        + f"\nContexto enviado pelo usuário/bot: {untrusted(tx.get('context'))}",
    )
    if out:
        extra = max(0, min(30, int(out.get("extra_risk") or 0)))
        risk = min(100, risk + extra)
        new_v = _from_score(risk)
        if ORDER[new_v] > ORDER[verdict]:
            verdict = new_v
        reasons += [r for r in out.get("extra_reasons") or [] if isinstance(r, str)][:3]
        if isinstance(out.get("explanation_ptbr"), str) and out["explanation_ptbr"].strip():
            explanation, used_llm = out["explanation_ptbr"].strip(), True

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
        "intent_hash": intent_hash(tx.get("chain_id", 1), tx["from"], tx["to"], tx.get("value", "0"), tx.get("data", "0x")),
        "report_hash": report_hash(report),
        "llm_used": used_llm or any(u for _, u in state.get("llm_calls", [])),
    }
    return {"verdict": result}
