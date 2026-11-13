"""Agente de Política — 100% determinístico (o LLM não decide regra). Dono: Rafael.
Contrato (TRD §3): entrada `tx`, `decoded`, `policy`; sem ferramentas; saída {violations[], warnings[], allowed}.
`violations` = regra descumprida (BLOQUEAR). `warnings` = regra que não pôde ser conferida (ALERTAR).
Regras (docs/05-backend-schema.md §4): max_value_usd, allowlist, block_unlimited_approvals,
allowed_hours, min_contract_age_days."""
from datetime import datetime, timezone

from tools.decode import fmt_br

TRANSFERS = ("transfer", "transferFrom", "native_transfer")
MOVES_VALUE = (*TRANSFERS, "approve", "swap")


def fmt_age(days: float) -> str:
    """0.08 -> '2 horas' · 3.5 -> '3,5 dias'."""
    if days < 1:
        h = max(1, round(days * 24))
        return f"{h} hora{'s' if h != 1 else ''}"
    return f"{fmt_br(days, 1)} dias"


def _num(v) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def destinations(tx: dict, d: dict) -> list[str]:
    """Quem a allowlist precisa aprovar: quem recebe os fundos ou a permissão.
    Em um swap: o contrato de troca e, se a saída for para outra carteira, também essa carteira."""
    a = d["action"]
    if a in TRANSFERS:
        dests = [d.get("recipient")]
    elif a == "approve":
        dests = [d.get("spender")]
    elif a == "swap":
        out = d.get("recipient")
        dests = [tx["to"], out if out and out.lower() != tx["from"].lower() else None]
    else:
        dests = [tx["to"]]
    return list(dict.fromkeys(x.lower() for x in dests if x))


def evaluate(tx: dict, d: dict, pol: dict, now_hour: int | None = None) -> list[str]:
    """Regras que só dependem da transação decodificada."""
    v: list[str] = []

    if pol.get("block_unlimited_approvals") and d["action"] == "approve":
        if d["is_unlimited"]:
            v.append("Política proíbe permissões ilimitadas de tokens.")
        elif d.get("function") == "increaseAllowance":
            # o valor é SOMADO à permissão que já existe: não dá para garantir que o total fica limitado
            v.append("increaseAllowance soma à permissão já existente; não é possível garantir que a "
                     "permissão final é limitada, e a política proíbe permissões ilimitadas.")

    limit, usd = _num(pol.get("max_value_usd")), d.get("amount_usd")
    if limit is not None and usd is not None and usd > limit:
        v.append(f"Valor (US$ {fmt_br(usd, 2)}) acima do limite da política (US$ {fmt_br(limit, 2)}).")

    allow = [a.lower() for a in pol.get("allowlist") or [] if isinstance(a, str)]
    if allow:
        for dest in destinations(tx, d):
            if dest not in allow:
                v.append(f"Destino {dest} não está na lista de permitidos.")

    hours = pol.get("allowed_hours") or [0, 24]
    if len(hours) == 2 and all(_num(h) is not None for h in hours):
        start, end = hours
        h = datetime.now(timezone.utc).hour if now_hour is None else now_hour   # horário da política é UTC
        inside = start <= h < end if start <= end else (h >= start or h < end)
        if not inside:
            v.append(f"Fora do horário permitido ({start}h–{end}h UTC).")
    return v


def unverified_limit(d: dict, pol: dict) -> list[str]:
    """Token sem preço ou sem decimais conhecidos: sem valor em USD o limite não pode ser conferido.
    Não é violação (a regra não foi descumprida) nem regra cumprida: vira ALERTAR, nunca PERMITIR."""
    limit = _num(pol.get("max_value_usd"))
    if limit is None or d.get("amount_usd") is not None or d["action"] not in MOVES_VALUE or d["is_unlimited"]:
        return []
    return [f"Não foi possível calcular o valor em USD desta transação; o limite de "
            f"US$ {fmt_br(limit, 2)} por transação não pôde ser conferido."]


def contract_age_violations(pol: dict, contracts: dict[str, dict]) -> list[str]:
    """Regra `min_contract_age_days`. A idade vem do Agente de Ameaças (contract_info), que roda em
    paralelo à Política; por isso quem chama esta função é o Juiz, ao consolidar as evidências."""
    min_age = _num(pol.get("min_contract_age_days"))
    if not min_age or min_age <= 0:
        return []
    out = []
    for addr, info in contracts.items():
        if info.get("is_contract") is False:
            continue                    # carteira comum: não tem data de criação
        age = _num(info.get("age_days"))
        if age is None:                 # sabe-se que é contrato, mas não a idade: a regra não pode ser dada como cumprida
            out.append(f"Não foi possível confirmar a idade do contrato {addr}; a política exige no mínimo {fmt_br(min_age, 1)} dias.")
        elif age < min_age:
            out.append(f"Contrato {addr} foi criado há {fmt_age(age)}; a política exige no mínimo {fmt_br(min_age, 1)} dias.")
    return out


def policy_node(state: dict) -> dict:
    pol = state.get("policy") or {}
    v = evaluate(state["tx"], state["decoded"], pol)
    return {"policy_result": {"allowed": not v, "violations": v, "warnings": unverified_limit(state["decoded"], pol)}}
