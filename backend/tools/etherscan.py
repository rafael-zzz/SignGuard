"""Reputação básica de contratos via Etherscan API v2. Dono: Dávila."""
import time

import httpx

from api.config import ETHERSCAN_API_KEY, OFFLINE

API = "https://api.etherscan.io/v2/api"
_cache: dict[str, dict] = {}


def _get(params: dict) -> dict | None:
    if OFFLINE or not ETHERSCAN_API_KEY:
        return None
    try:
        r = httpx.get(API, params={**params, "apikey": ETHERSCAN_API_KEY}, timeout=8).json()
        return r if r.get("status") == "1" else None
    except Exception:  # noqa: BLE001
        return None


def contract_info(address: str, chain_id: int = 1, offline: dict | None = None) -> dict:
    """{is_contract, verified, age_days, creator, source}. Campos None = desconhecido."""
    a = address.lower()
    if offline and a in offline.get("contract_info", {}):
        return {**offline["contract_info"][a], "source": "fixture"}
    if a in _cache:
        return _cache[a]

    info = {"is_contract": None, "verified": None, "age_days": None, "creator": None, "source": "etherscan"}
    src = _get({"chainid": chain_id, "module": "contract", "action": "getsourcecode", "address": a})
    if src:
        res = src["result"][0]
        info["verified"] = bool(res.get("SourceCode"))
    creation = _get({"chainid": chain_id, "module": "contract", "action": "getcontractcreation", "contractaddresses": a})
    if creation and creation.get("result"):
        c = creation["result"][0]
        info["is_contract"] = True
        info["creator"] = c.get("contractCreator")
        ts = c.get("timestamp")
        if ts:
            info["age_days"] = round((time.time() - int(ts)) / 86400, 2)
    elif creation is not None:
        info["is_contract"] = False
    if info["verified"] is None and info["is_contract"] is None:
        info["source"] = "indisponível"
    _cache[a] = info
    return info
