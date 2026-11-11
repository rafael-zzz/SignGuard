"""Reputação básica de contratos via Etherscan API v2. Dono: Dávila."""
import time

import httpx

from api.config import ETHERSCAN_API_KEY, OFFLINE

API = "https://api.etherscan.io/v2/api"
CACHE_TTL = 300
_cache: dict[tuple[int, str], tuple[float, dict]] = {}


def _get(params: dict) -> dict | None:
    if OFFLINE or not ETHERSCAN_API_KEY:
        return None
    try:
        response = httpx.get(API, params={**params, "apikey": ETHERSCAN_API_KEY}, timeout=8)
        response.raise_for_status()
        r = response.json()
        return r if isinstance(r, dict) and r.get("status") == "1" and isinstance(r.get("result"), list) else None
    except Exception:  # noqa: BLE001
        return None


def contract_info(address: str, chain_id: int = 1, offline: dict | None = None) -> dict:
    """{is_contract, verified, age_days, creator, source}. Campos None = desconhecido."""
    a = address.lower()
    if offline and a in offline.get("contract_info", {}):
        return {**offline["contract_info"][a], "source": "fixture"}
    key = (chain_id, a)
    if not OFFLINE and key in _cache:
        cached_at, cached = _cache[key]
        if time.monotonic() - cached_at < CACHE_TTL:
            return dict(cached)

    info = {"is_contract": None, "verified": None, "age_days": None, "creator": None, "source": "etherscan"}
    src = _get({"chainid": chain_id, "module": "contract", "action": "getsourcecode", "address": a})
    if src and src["result"] and isinstance(src["result"][0], dict):
        res = src["result"][0]
        info["verified"] = bool(res.get("SourceCode"))
    creation = _get({"chainid": chain_id, "module": "contract", "action": "getcontractcreation", "contractaddresses": a})
    if creation and creation.get("result") and isinstance(creation["result"][0], dict):
        c = creation["result"][0]
        info["is_contract"] = True
        info["creator"] = c.get("contractCreator")
        ts = c.get("timestamp")
        if ts:
            try:
                age = (time.time() - int(ts)) / 86400
                info["age_days"] = round(age, 2) if age >= 0 else None
            except (ValueError, TypeError):
                pass
    elif creation is not None:
        info["is_contract"] = False
    if info["verified"] is None and info["is_contract"] is None:
        info["source"] = "indisponível"
    if info["source"] != "indisponível":
        _cache[key] = (time.monotonic(), dict(info))
    return info
