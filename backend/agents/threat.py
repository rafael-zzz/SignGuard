"""Agente de Ameaças. Dono: Rafael (tools: Dávila).
Coleta sinais objetivos (código) + padrões de golpe (RAG). Pesos ajustáveis aqui."""
import re

from api import db
from tools.decode import fmt_br
from tools.etherscan import contract_info
from tools.rag import search_patterns

WEIGHTS = {
    "BLOCKLISTED": 100,
    "UNLIMITED_APPROVAL": 35,
    "CONTRACT_NEW": 25,
    "UNVERIFIED": 20,
    "SIMULATION_FAILED": 40,
    "UNKNOWN_FUNCTION": 30,
    "PROMPT_INJECTION": 30,
    "HIGH_VALUE": 15,
}

INJECTION_HINTS = re.compile(
    r"(ignore|ignorar|desconsidere|esque[çc]a).{0,40}(instru|regra|anterior)|"
    r"(system prompt|modo desenvolvedor|developer mode|jailbreak)|"
    r"(transfira|envie|mande).{0,30}(todo|tudo|saldo)",
    re.I,
)


def threat_node(state: dict) -> dict:
    tx, d = state["tx"], state["decoded"]
    offline = state.get("offline") or {}
    signals: list[dict] = []

    def add(code: str, evidence: str):
        signals.append({"code": code, "weight": WEIGHTS[code], "evidence": evidence})

    counterparty = d.get("spender") or d.get("recipient")
    addrs = [a for a in {tx["to"], counterparty} if a]

    for hit in db.blocklist_hits(addrs):
        add("BLOCKLISTED", f"{hit['address']} — {hit['label']} (fonte: {hit['source']})")

    if d["action"] == "approve" and d["is_unlimited"]:
        add("UNLIMITED_APPROVAL", f"approve ilimitado de {d.get('token_symbol')} para {d.get('spender')}")

    if d["action"] == "unknown":
        add("UNKNOWN_FUNCTION", f"função {d.get('function')} não reconhecida")

    if d.get("simulation_ok") is False:
        add("SIMULATION_FAILED", "a simulação reverteu")

    if (d.get("amount_usd") or 0) >= 1000:
        add("HIGH_VALUE", f"valor estimado US$ {fmt_br(d['amount_usd'], 2)}")

    # Reputação do contrato que recebe a permissão (approve) ou que é chamado
    target = d.get("spender") if d["action"] == "approve" else (tx["to"] if d["action"] == "unknown" else None)
    info = None
    if target:
        info = contract_info(target, tx.get("chain_id", 1), offline)
        if info.get("age_days") is not None and info["age_days"] < 7:
            add("CONTRACT_NEW", f"contrato criado há {info['age_days']} dias")
        if info.get("verified") is False:
            add("UNVERIFIED", "código-fonte não verificado no Etherscan")

    if tx.get("context") and INJECTION_HINTS.search(tx["context"]):
        add("PROMPT_INJECTION", "o contexto contém instruções típicas de manipulação de agente")

    tags = [s["code"] for s in signals] + [d["action"]]
    patterns = [p["title"] for p in search_patterns(tags)]
    risk = min(100, sum(s["weight"] for s in signals))
    return {"threat": {"signals": signals, "risk_score": risk, "patterns": patterns}}
