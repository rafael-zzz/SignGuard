"""Agente Decodificador. Dono: Rafael (tools: Dávila)."""
import json

from agents import llm
from agents.prompts import DECODER_SYSTEM, untrusted
from tools.decode import decode_calldata, known_contract_name
from tools.simulate import simulate_tx


def _short(a: str | None) -> str:
    return f"{a[:6]}…{a[-4:]}" if a and len(a) > 12 else (a or "?")


def template_summary(d: dict) -> str:
    a = d["action"]
    sym = d.get("token_symbol") or "tokens"
    if a == "approve":
        who = known_contract_name(d.get("spender")) or f"o endereço {_short(d.get('spender'))}"
        qty = "TODOS os seus" if d["is_unlimited"] else f"até {d['amount']}"
        return f"Você está dando permissão para {who} gastar {qty} {sym}, sem precisar pedir de novo."
    if a in ("transfer", "transferFrom"):
        return f"Você está enviando {d['amount']} {sym} para {_short(d.get('recipient'))}."
    if a == "native_transfer":
        return f"Você está enviando {d['amount']} ETH para {_short(d.get('recipient'))}."
    if a == "swap":
        return f"Você está trocando {d['amount']} ETH por {d.get('swap_out_symbol', 'tokens')} via {d.get('recipient_name') or 'um contrato de troca'}."
    return "Não foi possível identificar o que esta transação faz. Assinar assim é assinar às cegas."


def decoder_node(state: dict) -> dict:
    tx = state["tx"]
    offline = state.get("offline") or {}
    d = decode_calldata(tx["to"], tx.get("data", "0x"), tx.get("value", "0"))
    if d["action"] == "swap":
        d["recipient_name"] = known_contract_name(tx["to"])
    sim = simulate_tx(tx, d, offline)
    summary = template_summary(d)
    d.pop("recipient_name", None)

    used_llm = False
    out = llm.chat_json(
        DECODER_SYSTEM,
        "Transação decodificada por código (confiável):\n"
        + json.dumps({k: v for k, v in d.items() if k != "raw_args"}, ensure_ascii=False)
        + f"\nResumo-base: {summary}\nContexto enviado pelo usuário/bot: {untrusted(tx.get('context'))}",
    )
    if out and isinstance(out.get("summary_ptbr"), str) and out["summary_ptbr"].strip():
        summary, used_llm = out["summary_ptbr"].strip(), True

    decoded = {
        "action": d["action"], "function": d["function"], "token": d["token"],
        "token_symbol": d["token_symbol"], "spender": d["spender"], "recipient": d["recipient"],
        "amount": d["amount"], "amount_usd": d["amount_usd"], "is_unlimited": d["is_unlimited"],
        "simulation_ok": sim["ok"], "balance_changes": sim["balance_changes"], "summary_ptbr": summary,
    }
    return {"decoded": decoded, "llm_calls": [("decoder", used_llm)]}
