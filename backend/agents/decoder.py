"""Agente Decodificador. Dono: Rafael (tools: Dávila).
Contrato (TRD §3): entrada `tx`; ferramentas `decode_calldata` e `simulate_tx`;
saída {action, token, spender, amount, is_unlimited, balance_changes[], summary_ptbr}.
Os fatos vêm do código. O LLM só reescreve o resumo em linguagem simples, e o texto dele
só é aceito se passar no schema e bater com os fatos decodificados."""
import re
import time

from agents import llm
from agents.prompts import DECODER_SYSTEM, DecoderOut, decoder_user_prompt
from api.config import MAINNET_RPC_URL, OFFLINE
from tools.decode import decode_calldata, known_contract_name
from tools.etherscan import contract_info
from tools.simulate import simulate_tx

_URL = re.compile(r"https?://|www\.", re.I)
_ADDR = re.compile(r"0x[a-fA-F0-9]{40}")
_ADVICE = re.compile(r"\bassin[ea]\b|pode assinar|assinar agora|\bsegur[oa]\b|sem risco|confi[ea]\b", re.I)
_UNLIMITED = re.compile(r"ilimitad|sem limite|tod[oa]s|tudo|qualquer (quantia|valor)", re.I)


def _short(a: str | None) -> str:
    return f"{a[:6]}…{a[-4:]}" if a and len(a) > 12 else (a or "?")


def template_summary(d: dict) -> str:
    a = d["action"]
    sym = d.get("token_symbol") or "tokens"
    if sym == "TOKEN?":
        sym = f"de um token não reconhecido ({_short(d.get('token'))})"
    qty_known = d.get("amount") is not None
    if a == "approve":
        who = known_contract_name(d.get("spender")) or f"o endereço {_short(d.get('spender'))}"
        qty = "TODOS os seus" if d["is_unlimited"] else (
            f"até {d['amount']}" if qty_known else "uma quantidade que não foi possível calcular")
        extra = " A permissão é somada à que já existe." if d.get("function") == "increaseAllowance" else ""
        return f"Você está dando permissão para {who} gastar {qty} {sym}, sem precisar pedir de novo.{extra}"
    if a in ("transfer", "transferFrom"):
        qty = d["amount"] if qty_known else "uma quantidade que não foi possível calcular"
        return f"Você está enviando {qty} {sym} para {_short(d.get('recipient'))}."
    if a == "native_transfer":
        return f"Você está enviando {d['amount']} ETH para {_short(d.get('recipient'))}."
    if a == "swap":
        return f"Você está trocando {d['amount']} ETH por {d.get('swap_out_symbol', 'tokens')} via {d.get('recipient_name') or 'um contrato de troca'}."
    if d.get("to_contract"):
        return (f"Você está enviando {d['amount']} ETH para um contrato ({_short(d['to_contract'])}), que executa "
                "código próprio ao receber. Não foi possível identificar o que ele faz com esse valor.")
    return "Não foi possível identificar o que esta transação faz. Assinar assim é assinar às cegas."


def _undecodable(tx: dict) -> dict:
    data = (tx.get("data") or "0x").lower()
    return {"action": "unknown", "function": data[:10], "token": None, "token_symbol": None,
            "spender": None, "recipient": None, "amount": None, "amount_usd": None,
            "is_unlimited": False, "raw_args": None}


def _addresses(value) -> list[str]:
    """Todo endereço que aparece nos argumentos do calldata (origem do transferFrom, caminho do swap…)."""
    if isinstance(value, str):
        return [value.lower()] if _ADDR.fullmatch(value) else []
    if isinstance(value, (list, tuple)):
        return [a for item in value for a in _addresses(item)]
    return []


def summary_is_grounded(summary: str, d: dict, tx: dict) -> bool:
    """O resumo do LLM não pode trazer link, endereço que não está na transação,
    nem esconder que a permissão é ilimitada."""
    if _URL.search(summary) or _ADVICE.search(summary):   # o Decodificador descreve; quem recomenda é o Juiz
        return False
    if d["is_unlimited"] and not _UNLIMITED.search(summary):
        return False
    known = {(a or "").lower() for a in (tx.get("from"), tx.get("to"), d.get("token"), d.get("spender"), d.get("recipient"))}
    return all(a.lower() in known for a in _ADDR.findall(summary))


def decoder_node(state: dict) -> dict:
    tx = state["tx"]
    offline = state.get("offline") or {}
    errors: list[str] = []

    try:
        d = decode_calldata(tx["to"], tx.get("data") or "0x", tx.get("value") or "0", tx.get("chain_id", 1))
    except Exception as e:  # noqa: BLE001 — calldata malformado não derruba a análise: vira "desconhecido"
        d = _undecodable(tx)
        errors.append(f"decoder: calldata não pôde ser decodificado ({type(e).__name__})")
    if d["action"] == "swap":
        d["recipient_name"] = known_contract_name(tx["to"])
    if d["action"] == "native_transfer":
        # ETH enviado a um contrato executa o código dele (receive/fallback): não é um envio simples
        try:
            is_contract = contract_info(tx["to"], tx.get("chain_id", 1), offline).get("is_contract")
        except Exception as e:  # noqa: BLE001
            is_contract = None
            errors.append(f"decoder: não foi possível verificar se o destino é contrato ({type(e).__name__})")
        if is_contract:
            d.update(action="unknown", recipient=None, to_contract=tx["to"].lower())
    involved = _addresses(d.get("raw_args"))

    try:
        sim = simulate_tx(tx, d, offline)
    except Exception as e:  # noqa: BLE001
        sim = {"ok": None, "detail": f"erro na simulação ({type(e).__name__})", "balance_changes": []}
    # Simulação tentada = veio de fixture ou há RPC configurado. Tentada e sem resultado é falha;
    # não tentada (OFFLINE / sem RPC) é só evidência indisponível.
    attempted = "simulation_ok" in offline or bool(MAINNET_RPC_URL and not OFFLINE)
    if sim["ok"] is None:
        errors.append(f"decoder: simulação sem resultado ({sim['detail']})")

    summary = template_summary(d)
    d.pop("recipient_name", None)
    to_contract = d.pop("to_contract", None)

    used_llm, llm_seconds = False, 0.0
    if d["action"] != "unknown":  # sem decodificação não há fato para o LLM reescrever
        facts = {k: v for k, v in d.items() if k != "raw_args"}
        started = time.monotonic()
        out, err = llm.chat_structured(DECODER_SYSTEM, decoder_user_prompt(facts, summary), DecoderOut,
                                       timeout=llm.DECODER_BUDGET_S)
        llm_seconds = time.monotonic() - started
        if err:
            errors.append(f"decoder: {err}")
        if out:
            if summary_is_grounded(out.summary_ptbr, d, tx):
                summary, used_llm = out.summary_ptbr, True
            else:
                errors.append("decoder: resumo do LLM descartado por não bater com os dados decodificados")

    decoded = {
        "action": d["action"], "function": d["function"], "token": d["token"],
        "token_symbol": d["token_symbol"], "spender": d["spender"], "recipient": d["recipient"],
        "amount": d["amount"], "amount_usd": d["amount_usd"], "is_unlimited": d["is_unlimited"],
        "simulation_ok": sim["ok"], "balance_changes": sim["balance_changes"], "summary_ptbr": summary,
    }
    return {
        "decoded": decoded,
        "simulation": {"ok": sim["ok"], "detail": sim["detail"], "attempted": attempted,
                       "balance_changes_source": sim.get("balance_changes_source")},
        "involved": involved,
        "to_contract": to_contract,
        "llm_calls": [("decoder", used_llm)],
        "llm_seconds": llm_seconds,
        "errors": errors,
    }
