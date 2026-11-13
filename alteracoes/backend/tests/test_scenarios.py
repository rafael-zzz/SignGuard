"""Os 4 cenários da demo precisam dar o veredito esperado. Rodar: OFFLINE=1 pytest -q (de dentro de backend/)"""
import json

import pytest

from agents.graph import analyze
from api import db
from api.config import FIXTURES_DIR

db.init_db()
FIXTURES = [json.loads(f.read_text(encoding="utf-8")) for f in sorted(FIXTURES_DIR.glob("*.json"))]


@pytest.mark.parametrize("fx", FIXTURES, ids=[f["id"] for f in FIXTURES])
def test_expected_verdict(fx):
    v = analyze(fx["tx"], db.get_policy(fx["tx"]["owner_id"]), fx["offline"])
    assert v["verdict"] == fx["expected"], v["reasons"]
    assert v["explanation_ptbr"]
    assert v["intent_hash"].startswith("0x") and len(v["intent_hash"]) == 66
