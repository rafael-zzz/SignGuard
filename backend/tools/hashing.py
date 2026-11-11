import json

from eth_abi import encode
from eth_utils import keccak, to_checksum_address


def intent_hash(chain_id: int, sender: str, to: str, value: str, data: str) -> str:
    """Igual o SignGuardRegistry.intentHash: keccak256(abi.encode(chainId, from, to, value, data))."""
    raw = bytes.fromhex((data or "0x")[2:])
    enc = encode(["uint256", "address", "address", "uint256", "bytes"],
                 [chain_id, to_checksum_address(sender), to_checksum_address(to), int(value or "0"), raw])
    return "0x" + keccak(enc).hex()


def report_hash(report: dict) -> str:
    canon = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "0x" + keccak(canon.encode()).hex()
