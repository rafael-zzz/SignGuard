"""Agente de Política — 100% determinístico (o LLM não decide regra). Dono: Rafael.
Contrato (TRD §3): entrada `tx`, `decoded`, `policy`; sem ferramentas; saída {violations[], allowed}.
Regras (docs/05-backend-schema.md §4): max_value_usd, allowlist, block_unlimited_approvals,
allowed_hours, min_contract_age_days."""
from datetime import datetime

from tools.decode import fmt_br

TRANSFERS = ("transfer", "transferFrom", "native_transfer")


def fmt_age(days: float) -> str:
    """0.08 -> '2 horas' · 3.5 -> '3,5 dias'."""
    if days < 1:
        h = max(1, round(days * 24))
        return f"{h} hora{'s' if h != 1 else ''}"
    return f"{fmt_br(days, 1)} dias"


def _num(v) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def evaluate(tx: dict, d: dict, pol: dict, now_hour: int | None = None) -> list[str]:
    """Regras que só dependem da transação decodificada."""
    v: list[str] = []

    if pol.get("block_unlimited_approvals") and d["action"] == "approve" and d["is_unlimited"]:
        v.append("Política proíbe permissões ilimitadas de tokens.")

    limit, usd = _num(pol.get("max_value_usd")), d.get("amount_usd")
    if limit is not None and usd is not None and usd > limit:
        v.append(f"Valor (US$ {fmt_br(usd, 2)}) acima do limite da política (US$ {fmt_br(limit, 2)}).")

    allow = [a.lower() for a in pol.get("allowlist") or [] if isinstance(a, str)]
    if allow:
        dest = d.get("recipient") if d["action"] in TRANSFERS else (d.get("spender") or tx["to"])
        if dest and dest.lower() not in allow:
            v.append(f"Destino {dest} não está na lista de permitidos.")

    hours = pol.get("allowed_hours") or [0, 24]
    if len(hours) == 2 and all(_num(h) is not None for h in hours):
        start, end = hours
        h = datetime.now().hour if now_hour is None else now_hour
        inside = start <= h < end if start <= end else (h >= start or h < end)
        if not inside:
            v.append(f"Fora do horário permitido ({start}h–{end}h).")
    return v


def contract_age_violations(pol: dict, contracts: dict[str, dict]) -> list[str]:
    """Regra `min_contract_age_days`. A idade vem do Agente de Ameaças (contract_info), que roda em
    paralelo à Política; por isso quem chama esta função é o Juiz, ao consolidar as evidências."""
    min_age = _num(pol.get("min_contract_age_days"))
    if not min_age or min_age <= 0:
        return []
    out = []
    for addr, info in contracts.items():
        age = _num(info.get("age_days"))
        if age is not None and age < min_age:
            out.append(f"Contrato {addr} foi criado há {fmt_age(age)}; a política exige no mínimo {fmt_br(min_age, 1)} dias.")
    return out


def policy_node(state: dict) -> dict:
    v = evaluate(state["tx"], state["decoded"], state.get("policy") or {})
    return {"policy_result": {"allowed": not v, "violations": v}}
