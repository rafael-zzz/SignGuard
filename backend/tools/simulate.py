"""Simulação da transação. Dono: Dávila.
MVP: eth_call no RPC (idealmente um Anvil com fork da mainnet) para saber se a tx reverte.
Mudanças de saldo vêm do decode (ERC-20/ETH). Próximo passo: debug_traceCall para capturar
Transfer events reais (pega drainers que escondem o efeito atrás de chamadas internas).

Rodar o fork:  anvil --fork-url $MAINNET_RPC_URL --port 8545
e usar MAINNET_RPC_URL=http://127.0.0.1:8545 no .env."""
import httpx

from api.config import MAINNET_RPC_URL, OFFLINE


def eth_call(tx: dict) -> tuple[bool | None, str]:
    """Retorna (ok, detalhe). ok=None quando não foi possível simular."""
    if OFFLINE or not MAINNET_RPC_URL:
        return None, "simulação desligada (OFFLINE ou sem RPC)"
    payload = {
        "jsonrpc": "2.0", "id": 1, "method": "eth_call",
        "params": [{"from": tx["from"], "to": tx["to"], "data": tx.get("data") or "0x",
                    "value": hex(int(tx.get("value") or "0"))}, "latest"],
    }
    try:
        r = httpx.post(MAINNET_RPC_URL, json=payload, timeout=8).json()
    except Exception as e:  # noqa: BLE001
        return None, f"erro de RPC: {e}"
    if "error" in r:
        return False, r["error"].get("message", "reverteu")
    return True, "executa sem reverter"


def simulate_tx(tx: dict, decoded: dict, offline: dict | None = None) -> dict:
    if offline and "simulation_ok" in offline:
        ok, detail = offline["simulation_ok"], "fixture"
    else:
        ok, detail = eth_call(tx)

    changes = []
    a = decoded.get("action")
    if a in ("transfer", "transferFrom") and decoded.get("amount"):
        changes.append({"token": decoded["token"], "symbol": decoded["token_symbol"], "delta": f"-{decoded['amount']}"})
    elif a in ("native_transfer", "swap") and decoded.get("amount"):
        changes.append({"token": "ETH", "symbol": "ETH", "delta": f"-{decoded['amount']}"})
    return {"ok": ok, "detail": detail, "balance_changes": changes}
