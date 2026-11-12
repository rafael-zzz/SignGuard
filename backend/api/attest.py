"""Registro do veredito on-chain no SignGuardRegistry (Sepolia). Dono: Davi.
Sem ATTESTER_PRIVATE_KEY/REGISTRY_ADDRESS/SEPOLIA_RPC_URL -> retorna mock (a demo não quebra)."""
from .config import ATTESTER_PRIVATE_KEY, REGISTRY_ADDRESS, SEPOLIA_EXPLORER, SEPOLIA_RPC_URL

SEPOLIA_CHAIN_ID = 11155111
VERDICT_CODE = {"ALLOW": 0, "WARN": 1, "BLOCK": 2}
VERDICT_NAME = {v: k for k, v in VERDICT_CODE.items()}

_ATTESTATION_TUPLE = {
    "name": "", "type": "tuple", "components": [
        {"name": "intentHash", "type": "bytes32"}, {"name": "target", "type": "address"},
        {"name": "verdict", "type": "uint8"}, {"name": "riskScore", "type": "uint8"},
        {"name": "reportHash", "type": "bytes32"}, {"name": "timestamp", "type": "uint64"},
        {"name": "attester", "type": "address"},
    ],
}
ABI = [
    {
        "type": "function", "name": "attest", "stateMutability": "nonpayable", "outputs": [],
        "inputs": [
            {"name": "intentHash", "type": "bytes32"}, {"name": "target", "type": "address"},
            {"name": "verdict", "type": "uint8"}, {"name": "riskScore", "type": "uint8"},
            {"name": "reportHash", "type": "bytes32"},
        ],
    },
    {
        "type": "function", "name": "getAttestation", "stateMutability": "view",
        "inputs": [{"name": "intentHash", "type": "bytes32"}], "outputs": [_ATTESTATION_TUPLE],
    },
    {
        "type": "function", "name": "reputation", "stateMutability": "view",
        "inputs": [{"name": "target", "type": "address"}],
        "outputs": [{"name": "attestations", "type": "uint32"}, {"name": "blocks", "type": "uint32"}],
    },
]


def configured() -> bool:
    return bool(ATTESTER_PRIVATE_KEY and REGISTRY_ADDRESS and SEPOLIA_RPC_URL)


def _read_configured() -> bool:
    return bool(REGISTRY_ADDRESS and SEPOLIA_RPC_URL)


def _bytes32(h: str) -> bytes:
    raw = bytes.fromhex(h.removeprefix("0x"))
    if len(raw) != 32:
        raise ValueError(f"hash inválido (esperado 32 bytes): {h}")
    return raw


def _hex(b: bytes) -> str:
    h = b.hex()
    return h if h.startswith("0x") else "0x" + h


def _contract():
    from web3 import Web3

    w3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC_URL, request_kwargs={"timeout": 20}))
    chain_id = w3.eth.chain_id
    if chain_id != SEPOLIA_CHAIN_ID:
        raise RuntimeError(f"SEPOLIA_RPC_URL aponta para a chain {chain_id}, esperado {SEPOLIA_CHAIN_ID}")
    c = w3.eth.contract(address=Web3.to_checksum_address(REGISTRY_ADDRESS), abi=ABI)
    return w3, c


def attest_onchain(result: dict, target: str) -> tuple[str | None, str | None, bool]:
    """Envia o atestado e retorna (tx_hash, explorer_url, mocked) sem esperar a mineração.
    Reverts (ex.: carteira não é attester) aparecem já na estimativa de gas e sobem como exceção."""
    if not configured():
        return None, None, True

    from web3 import Web3

    w3, c = _contract()
    acct = w3.eth.account.from_key(ATTESTER_PRIVATE_KEY)
    tx = c.functions.attest(
        _bytes32(result["intent_hash"]),
        Web3.to_checksum_address(target),
        VERDICT_CODE[result["verdict"]],
        int(result["risk_score"]),
        _bytes32(result["report_hash"]),
    ).build_transaction({
        "from": acct.address,
        # "pending" evita nonce repetido quando dois atestados saem antes do primeiro minerar
        "nonce": w3.eth.get_transaction_count(acct.address, "pending"),
        "chainId": SEPOLIA_CHAIN_ID,
    })
    signed = acct.sign_transaction(tx)
    h = _hex(w3.eth.send_raw_transaction(signed.raw_transaction))
    return h, f"{SEPOLIA_EXPLORER}/tx/{h}", False


def get_attestation(intent_hash: str) -> dict | None:
    """Lê o atestado de uma intenção. None se não houver registro ou se on-chain não estiver configurado."""
    if not _read_configured():
        return None
    _, c = _contract()
    a = c.functions.getAttestation(_bytes32(intent_hash)).call()
    intent, target, verdict, score, report, ts, attester = a
    if ts == 0:
        return None
    return {
        "intent_hash": _hex(intent), "target": target, "verdict": VERDICT_NAME[verdict],
        "risk_score": score, "report_hash": _hex(report), "timestamp": ts, "attester": attester,
    }


def reputation(target: str) -> dict | None:
    """Reputação pública de um endereço: quantos atestados e quantos BLOCK. None se não configurado."""
    if not _read_configured():
        return None
    from web3 import Web3

    _, c = _contract()
    total, blocks = c.functions.reputation(Web3.to_checksum_address(target)).call()
    return {"address": Web3.to_checksum_address(target), "attestations": total, "blocks": blocks}
