"""Simulação read-only com eth_call e trace opcional; nenhum envio de transação.
Saldos do trace usam eventos ERC-20 conhecidos e fluxos nativos relativos ao remetente.
Sem trace, o fallback é uma estimativa do calldata, identificada explicitamente.
"""
from collections import defaultdict

import httpx
from eth_utils import keccak

from tools.decode import TOKENS, _human

from api.config import MAINNET_RPC_URL, OFFLINE


def rpc_chain_matches(tx: dict) -> bool:
    """Sem cache: um endpoint reconfigurado não pode emprestar evidências de outra rede."""
    if OFFLINE or not MAINNET_RPC_URL or tx.get("chain_id", 1) != 1:
        return False
    try:
        response = httpx.post(MAINNET_RPC_URL, json={
            "jsonrpc": "2.0", "id": 10, "method": "eth_chainId", "params": [],
        }, timeout=4)
        response.raise_for_status()
        body = response.json()
        return isinstance(body, dict) and "error" not in body and int(body.get("result", ""), 16) == tx.get("chain_id", 1)
    except (httpx.HTTPError, ValueError, TypeError):
        return False


def contract_code(address: str, chain_id: int = 1) -> str | None:
    if not rpc_chain_matches({"chain_id": chain_id}):
        return None
    try:
        response = httpx.post(MAINNET_RPC_URL, json={
            "jsonrpc": "2.0", "id": 11, "method": "eth_getCode", "params": [address, "latest"],
        }, timeout=4)
        response.raise_for_status()
        body = response.json()
        code = body.get("result") if isinstance(body, dict) and "error" not in body else None
        if isinstance(code, str) and code.startswith("0x"):
            bytes.fromhex(code[2:])
            return code
    except (httpx.HTTPError, ValueError):
        pass
    return None


def eth_call(tx: dict) -> tuple[bool | None, str]:
    """Retorna (ok, detalhe). ok=None quando não foi possível simular."""
    if OFFLINE or not MAINNET_RPC_URL:
        return None, "simulação desligada (OFFLINE ou sem RPC)"
    if not rpc_chain_matches(tx):
        return None, "RPC indisponível, rede divergente ou não suportada"
    payload = {
        "jsonrpc": "2.0", "id": 1, "method": "eth_call",
        "params": [{"from": tx["from"], "to": tx["to"], "data": tx.get("data") or "0x",
                    "value": hex(int(tx.get("value") or "0"))}, "latest"],
    }
    try:
        response = httpx.post(MAINNET_RPC_URL, json=payload, timeout=8)
        response.raise_for_status()
        r = response.json()
    except (httpx.HTTPError, ValueError):
        return None, "RPC indisponível ou resposta inválida"
    if not isinstance(r, dict):
        return None, "resposta RPC inválida"
    if isinstance(r.get("error"), dict):
        error = r["error"]
        message = str(error.get("message", "erro RPC"))
        if error.get("code") == 3 or "revert" in message.lower() or message.startswith("EVM error"):
            return False, "execução falhou na EVM"
        return None, "RPC não conseguiu executar a simulação"
    result = r.get("result")
    if not isinstance(result, str) or not result.startswith("0x"):
        return None, "resposta RPC sem resultado válido"
    try:
        bytes.fromhex(result[2:])
    except ValueError:
        return None, "resultado RPC inválido"
    data = tx.get("data", "0x").lower()
    if data[:10] in {"0xa9059cbb", "0x23b872dd", "0x095ea7b3", "0x39509351"} and result == "0x" + "00" * 32:
        return False, "token retornou false"
    if data != "0x":
        code = contract_code(tx["to"], tx.get("chain_id", 1))
        if code is None or code == "0x":
            return None, "não foi possível confirmar código no destino do calldata"
    return True, "executa sem reverter"


def simulate_tx(tx: dict, decoded: dict | None = None, offline: dict | None = None) -> dict:
    if decoded is None:
        from tools.decode import decode_calldata
        decoded = decode_calldata(tx["to"], tx.get("data", "0x"), tx.get("value", "0"), tx.get("chain_id", 1))
    if offline and "simulation_ok" in offline:
        ok, detail = offline["simulation_ok"], "fixture"
    else:
        ok, detail = eth_call(tx)

    if ok is True and offline and "balance_changes" in offline:
        return {"ok": ok, "detail": detail, "balance_changes": offline["balance_changes"],
                "balance_changes_source": "fixture", "trace": offline.get("trace")}
    trace = None
    if ok is True and not offline:
        trace = trace_call(tx)
        if trace is not None:
            try:
                changes = trace_balance_changes(trace, tx["from"])
            except (ValueError, TypeError, AttributeError):
                trace = None
            else:
                return {"ok": ok, "detail": detail, "balance_changes": changes,
                        "balance_changes_source": "trace", "trace": trace}
    changes = []
    a = decoded.get("action") if ok is True else None
    if a in ("transfer", "transferFrom") and decoded.get("amount"):
        sender = tx["from"].lower()
        source = sender if a == "transfer" else decoded["raw_args"][0].lower()
        direction = int(decoded["recipient"].lower() == sender) - int(source == sender)
        if direction:
            delta = ("-" if direction < 0 else "") + decoded["amount"]
            changes.append({"token": decoded["token"], "symbol": decoded["token_symbol"], "delta": delta})
    elif a in ("native_transfer", "swap") and decoded.get("amount"):
        changes.append({"token": "ETH", "symbol": "ETH", "delta": f"-{decoded['amount']}"})
    return {"ok": ok, "detail": detail, "balance_changes": changes,
            "balance_changes_source": "estimativa do calldata" if changes else None,
            "trace": None}


TRANSFER_TOPIC = "0x" + keccak(text="Transfer(address,address,uint256)").hex()


def trace_call(tx: dict) -> dict | None:
    """callTracer é opcional: RPCs sem debug mantêm o resultado de eth_call."""
    if not rpc_chain_matches(tx):
        return None
    try:
        response = httpx.post(MAINNET_RPC_URL, json={
            "jsonrpc": "2.0", "id": 2, "method": "debug_traceCall",
            "params": [{"from": tx["from"], "to": tx["to"], "data": tx.get("data", "0x"),
                        "value": hex(int(tx.get("value", "0")))}, "latest",
                       {"tracer": "callTracer", "tracerConfig": {"withLog": True}}],
        }, timeout=2)
        response.raise_for_status()
        body = response.json()
        result = body.get("result") if isinstance(body, dict) else None
        if isinstance(result, dict) and result.get("type") and not result.get("error"):
            return result
    except (httpx.HTTPError, ValueError):
        pass
    return None


def trace_balance_changes(trace: dict, sender: str) -> list[dict]:
    """Somente fluxos efetivos de chamadas não revertidas; não inclui gas.

    Eventos não provam saldo para tokens não padrão. Tokens desconhecidos são
    omitidos porque não há metadados confiáveis de símbolo/decimais.
    """
    sender = sender.lower()
    deltas = defaultdict(int)
    stack = [trace]
    while stack:
        call = stack.pop()
        if not isinstance(call, dict) or call.get("error"):
            continue
        stack.extend(call.get("calls", []))
        if call.get("type", "").upper() in {"CALL", "CREATE", "CREATE2", "SELFDESTRUCT"}:
            value = int(call.get("value", "0x0"), 16)
            if call.get("from", "").lower() == sender:
                deltas["ETH"] -= value
            if call.get("to", "").lower() == sender:
                deltas["ETH"] += value
        for log in call.get("logs", []):
            token = log.get("address", "").lower()
            topics = log.get("topics", [])
            if token not in TOKENS or len(topics) != 3 or topics[0].lower() != TRANSFER_TOPIC:
                continue
            try:
                if any(len(t) != 66 for t in topics) or len(log.get("data", "")) != 66:
                    continue
                value = int(log["data"], 16)
                if "0x" + topics[1][-40:].lower() == sender:
                    deltas[token] -= value
                if "0x" + topics[2][-40:].lower() == sender:
                    deltas[token] += value
            except (ValueError, TypeError):
                continue
    changes = []
    for token, delta in sorted(deltas.items()):
        if not delta:
            continue
        symbol, decimals = ("ETH", 18) if token == "ETH" else TOKENS[token][:2]
        changes.append({"token": token, "symbol": symbol, "delta": _human(delta, decimals)})
    return changes
