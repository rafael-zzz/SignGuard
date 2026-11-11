import json
import sqlite3
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from datetime import datetime, timezone

from .config import DB_PATH

DEFAULT_POLICIES = {
    # Usuário comum: sem allowlist, bloqueia approve ilimitado
    "default": {
        "max_value_usd": 5000,
        "allowlist": [],
        "block_unlimited_approvals": True,
        "allowed_hours": [0, 24],
        "min_contract_age_days": 7,
    },
    # Agente de IA com carteira (demo): só paga fornecedores conhecidos, até US$ 100
    "agent-wallet": {
        "max_value_usd": 100,
        "allowlist": ["0x5a3a1c2b9e4d7f60812a3b4c5d6e7f8091a2b3c4"],
        "block_unlimited_approvals": True,
        "allowed_hours": [0, 24],
        "min_contract_age_days": 7,
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def conn():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    try:
        with c:
            yield c
    finally:
        c.close()


def init_db() -> None:
    with conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS analyses (
              id TEXT PRIMARY KEY, created_at TEXT, owner_id TEXT,
              tx_json TEXT, verdict TEXT, risk_score INTEGER,
              result_json TEXT, report_hash TEXT
            );
            CREATE TABLE IF NOT EXISTS attestations (
              analysis_id TEXT REFERENCES analyses(id), chain_id INTEGER,
              tx_hash_onchain TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS policies (owner_id TEXT PRIMARY KEY, policy_json TEXT, updated_at TEXT);
            CREATE TABLE IF NOT EXISTS blocklist (address TEXT PRIMARY KEY, label TEXT, source TEXT);
            """
        )
        for owner, pol in DEFAULT_POLICIES.items():
            c.execute(
                "INSERT OR IGNORE INTO policies VALUES (?,?,?)", (owner, json.dumps(pol), _now())
            )
        # Endereços fictícios para a demo. Trocar por fontes reais (ex.: listas públicas de phishing).
        demo_block = [
            ("0xbad0000000000000000000000000000000c0ffee", "Golpe de falso suporte (demo)", "demo"),
            ("0x1337000000000000000000000000000000beef01", "Drainer conhecido (demo)", "demo"),
        ]
        c.executemany("INSERT OR IGNORE INTO blocklist VALUES (?,?,?)", demo_block)


def get_policy(owner_id: str) -> dict:
    with conn() as c:
        r = c.execute("SELECT policy_json FROM policies WHERE owner_id=?", (owner_id,)).fetchone()
    return json.loads(r["policy_json"]) if r else deepcopy(DEFAULT_POLICIES["default"])


def put_policy(owner_id: str, policy: dict) -> None:
    with conn() as c:
        c.execute(
            "INSERT INTO policies VALUES (?,?,?) ON CONFLICT(owner_id) DO UPDATE SET policy_json=excluded.policy_json, updated_at=excluded.updated_at",
            (owner_id, json.dumps(policy), _now()),
        )


def blocklist_hits(addresses: list[str]) -> list[dict]:
    addrs = [a.lower() for a in addresses if a]
    if not addrs:
        return []
    q = ",".join("?" * len(addrs))
    with conn() as c:
        rows = c.execute(f"SELECT * FROM blocklist WHERE lower(address) IN ({q})", addrs).fetchall()
    return [dict(r) for r in rows]


def save_analysis(verdict: dict, tx: dict) -> None:
    with conn() as c:
        c.execute(
            "INSERT INTO analyses VALUES (?,?,?,?,?,?,?,?)",
            (
                verdict["analysis_id"], _now(), tx.get("owner_id", "default"), json.dumps(tx),
                verdict["verdict"], verdict["risk_score"], json.dumps(verdict), verdict["report_hash"],
            ),
        )


def get_analysis(analysis_id: str) -> dict | None:
    with conn() as c:
        r = c.execute("SELECT * FROM analyses WHERE id=?", (analysis_id,)).fetchone()
    if not r:
        return None
    return {"tx": json.loads(r["tx_json"]), "result": json.loads(r["result_json"])}


def list_analyses(limit: int = 50) -> list[dict]:
    with conn() as c:
        rows = c.execute(
            "SELECT id, created_at, owner_id, verdict, risk_score FROM analyses ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def save_attestation(analysis_id: str, chain_id: int, tx_hash: str | None) -> None:
    with conn() as c:
        c.execute("INSERT INTO attestations VALUES (?,?,?,?)", (analysis_id, chain_id, tx_hash, _now()))


def check_blocklist(addresses: list[str]) -> list[dict]:
    """Nome público previsto em docs/05; preserva blocklist_hits para os agentes."""
    return blocklist_hits(addresses)
