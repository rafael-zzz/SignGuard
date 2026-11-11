"""Registro do veredito on-chain no SignGuardRegistry (Sepolia). Dono: Davi.
Sem ATTESTER_PRIVATE_KEY/REGISTRY_ADDRESS/SEPOLIA_RPC_URL -> retorna mock (a demo não quebra)."""
from .config import ATTESTER_PRIVATE_KEY, REGISTRY_ADDRESS, SEPOLIA_EXPLORER, SEPOLIA_RPC_URL

ABI = [{
    "type": "function", "name": "attest", "stateMutability": "nonpayable", "outputs": [],
    "inputs": [
        {"name": "intentHash", "type": "bytes32"}, {"name": "target", "type": "address"},
        {"name": "verdict", "type": "uint8"}, {"name": "riskScore", "type": "uint8"},
        {"name": "reportHash", "type": "bytes32"},
    ],
}]
VERDICT_CODE = {"ALLOW": 0, "WARN": 1, "BLOCK": 2}


def configured() -> bool:
    return bool(ATTESTER_PRIVATE_KEY and REGISTRY_ADDRESS and SEPOLIA_RPC_URL)


def attest_onchain(result: dict, target: str) -> tuple[str | None, str | None, bool]:
    """Retorna (tx_hash, explorer_url, mocked)."""
    if not configured():
        return None, None, True

    from web3 import Web3

    w3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC_URL))
    acct = w3.eth.account.from_key(ATTESTER_PRIVATE_KEY)
    c = w3.eth.contract(address=Web3.to_checksum_address(REGISTRY_ADDRESS), abi=ABI)
    tx = c.functions.attest(
        bytes.fromhex(result["intent_hash"][2:]),
        Web3.to_checksum_address(target),
        VERDICT_CODE[result["verdict"]],
        int(result["risk_score"]),
        bytes.fromhex(result["report_hash"][2:]),
    ).build_transaction({
        "from": acct.address,
        "nonce": w3.eth.get_transaction_count(acct.address),
        "chainId": 11155111,
    })
    signed = acct.sign_transaction(tx)
    h = w3.eth.send_raw_transaction(signed.raw_transaction).hex()
    h = h if h.startswith("0x") else "0x" + h
    return h, f"{SEPOLIA_EXPLORER}/tx/{h}", False
