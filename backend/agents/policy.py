"""Agente de Política — 100% determinístico (o LLM não decide regra). Dono: Rafael."""
from datetime import datetime

from tools.decode import fmt_br


def policy_node(state: dict) -> dict:
    d, pol = state["decoded"], state["policy"]
    v: list[str] = []

    if pol.get("block_unlimited_approvals") and d["action"] == "approve" and d["is_unlimited"]:
        v.append("Política proíbe permissões ilimitadas de tokens.")

    usd = d.get("amount_usd")
    if usd is not None and usd > pol.get("max_value_usd", float("inf")):
        v.append(f"Valor (US$ {fmt_br(usd, 2)}) acima do limite da política (US$ {fmt_br(pol['max_value_usd'], 2)}).")

    allow = [a.lower() for a in pol.get("allowlist", [])]
    if allow:
        dest = d.get("recipient") if d["action"] in ("transfer", "transferFrom", "native_transfer") else d.get("spender") or state["tx"]["to"]
        if dest and dest.lower() not in allow:
            v.append(f"Destino {dest} não está na lista de permitidos.")

    start, end = pol.get("allowed_hours", [0, 24])
    h = datetime.now().hour
    if not (start <= h < end):
        v.append(f"Fora do horário permitido ({start}h–{end}h).")

    return {"policy_result": {"allowed": not v, "violations": v}}
