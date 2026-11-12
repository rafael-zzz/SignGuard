"""Teste read-only do fork: python -m scripts.check_anvil (dentro de backend/)."""
import json

import httpx
from eth_abi import encode

from api.config import MAINNET_RPC_URL, OFFLINE
from tools.simulate import simulate_tx


def main():
    if OFFLINE or not MAINNET_RPC_URL:
        raise SystemExit("Defina OFFLINE=0 e MAINNET_RPC_URL apontando para o Anvil.")

    def rpc(method, params):
        response = httpx.post(MAINNET_RPC_URL, json={
            "jsonrpc": "2.0", "id": 1, "method": method, "params": params,
        }, timeout=30)
        response.raise_for_status()
        body = response.json()
        if "error" in body:
            raise RuntimeError(f"RPC falhou em {method}")
        return body["result"]

    version = rpc("web3_clientVersion", [])
    assert "anvil" in version.lower(), "o teste deve usar Anvil"
    assert int(rpc("eth_chainId", []), 16) == 1, "o fork deve ser mainnet"
    accounts = rpc("eth_accounts", [])
    assert len(accounts) >= 2, "Anvil precisa de duas contas locais de teste"
    sender, recipient = accounts[:2]
    tx = {"chain_id": 1, "from": sender, "to": recipient, "data": "0x", "value": str(10**16)}
    result = simulate_tx(tx)
    assert result["ok"] is True and result["balance_changes_source"] == "trace", result
    assert result["balance_changes"] == [{"token": "ETH", "symbol": "ETH", "delta": "-0,01"}]
    print("OK transferência nativa: eth_call + callTracer, delta -0,01 ETH")

    token = "0xdac17f958d2ee523a2206206994597c13d831ec7"
    assert rpc("eth_getCode", [token, "latest"]) != "0x", "USDT ausente no fork"
    args = encode(["address", "uint256"], [recipient, 10**6]).hex()
    tx.update(to=token, value="0", data="0x095ea7b3" + args)
    result = simulate_tx(tx)
    assert result["ok"] is True and result["trace"] is not None, result
    print("OK approve USDT: simulação no contrato mainnet")

    balance = int(rpc("eth_call", [{"to": token, "data": "0x70a08231" +
                   encode(["address"], [sender]).hex()}, "latest"]), 16)
    tx["data"] = "0xa9059cbb" + encode(["address", "uint256"], [recipient, balance + 1]).hex()
    result = simulate_tx(tx)
    assert result["ok"] is False and result["balance_changes"] == [], result
    print("OK transfer USDT acima do saldo: falha EVM, sem mudanças de saldo")
    print(json.dumps({"client": version, "block": int(rpc("eth_blockNumber", []), 16)}))


if __name__ == "__main__":
    main()
