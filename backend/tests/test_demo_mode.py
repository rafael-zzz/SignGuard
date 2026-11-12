"""Integração anônima explícita para a demo e isolamento Bearer no modo normal."""
import json

import pytest

from api import db, main
from api.config import FIXTURES_DIR
from test_backend import client, auth


def fixture(name="swap-legitimo"):
    return json.loads((FIXTURES_DIR / f"{name}.json").read_text())


@pytest.fixture
def anonymous(client):
    client.headers.pop("Authorization", None)
    return client


@pytest.mark.parametrize("name", ["approve-golpe", "swap-legitimo", "endereco-suspeito", "agente-manipulado"])
@pytest.mark.parametrize("route", ["scenario", "analyze"])
def test_demo_scenarios_without_tokens_keep_owner(anonymous, monkeypatch, name, route):
    monkeypatch.setenv("SIGNGUARD_DEMO_MODE", "1")
    monkeypatch.delenv("SIGNGUARD_API_KEYS", raising=False)
    fx = fixture(name)
    response = (anonymous.post(f"/analyze/scenario/{name}") if route == "scenario" else
                anonymous.post(f"/analyze?scenario_id={name}", json=fx["tx"]))
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["verdict"] == fx["expected"]
    stored = anonymous.get(f"/analyses/{result['analysis_id']}").json()
    assert stored["tx"] == fx["tx"]
    history = anonymous.get("/analyses").json()
    assert history[0]["owner_id"] == fx["tx"]["owner_id"]
    assert db.get_analysis(result["analysis_id"])["tx"]["owner_id"] == fx["tx"]["owner_id"]


def test_demo_other_routes_and_offline_attest(anonymous, monkeypatch):
    monkeypatch.setenv("SIGNGUARD_DEMO_MODE", "1")
    monkeypatch.setenv("SIGNGUARD_API_KEYS", "invalid-but-unused-in-demo")
    def no_broadcast(*args):
        pytest.fail("offline chamou o adaptador")
    monkeypatch.setattr(main.attest_mod, "attest_onchain", no_broadcast)
    result = anonymous.post("/analyze/scenario/agente-manipulado").json()
    assert anonymous.get("/policies/agent-wallet").status_code == 200
    policy = db.get_policy("agent-wallet")
    assert anonymous.put("/policies/agent-wallet", json=policy).json() == policy
    assert anonymous.post("/attest", json={"analysis_id": result["analysis_id"]}).json()["mocked"] is True
    assert anonymous.post("/forensic", json={"tx_hash": "demo"}).status_code == 200
    assert anonymous.post("/analyze/scenario/missing").status_code == 404
    assert anonymous.get("/analyses/missing").status_code == 404
    assert anonymous.post("/analyze", json={"from": "invalid"}).status_code == 422
    assert anonymous.put("/policies/default", json={}).status_code == 422
    assert anonymous.get("/health").json()["demo_mode"] is True


def test_demo_without_scenario_uses_tx_owner(anonymous, monkeypatch):
    monkeypatch.setenv("SIGNGUARD_DEMO_MODE", "1")
    tx = fixture("agente-manipulado")["tx"]
    response = anonymous.post("/analyze", json=tx)
    assert response.status_code == 200
    assert response.json()["verdict"] == "BLOCK"
    assert db.get_analysis(response.json()["analysis_id"])["tx"]["owner_id"] == "agent-wallet"


@pytest.mark.parametrize("flag", [None, "0", "", "false", "true", "yes", "01"])
def test_only_explicit_one_enables_demo(anonymous, monkeypatch, flag):
    if flag is None:
        monkeypatch.delenv("SIGNGUARD_DEMO_MODE", raising=False)
    else:
        monkeypatch.setenv("SIGNGUARD_DEMO_MODE", flag)
    assert anonymous.get("/health").json()["demo_mode"] is False
    assert anonymous.post("/analyze/scenario/swap-legitimo").status_code == 401
    assert anonymous.post("/analyze/scenario/swap-legitimo", headers=auth()).status_code == 200
    monkeypatch.delenv("SIGNGUARD_API_KEYS", raising=False)
    assert anonymous.get("/analyses").status_code == 503


def test_demo_does_not_replace_agent_owner_even_with_default_token(client, monkeypatch):
    monkeypatch.setenv("SIGNGUARD_DEMO_MODE", "1")
    result = client.post("/analyze/scenario/agente-manipulado").json()
    assert db.get_analysis(result["analysis_id"])["tx"]["owner_id"] == "agent-wallet"


def test_normal_mode_preserves_owner_authorization(anonymous):
    assert anonymous.post("/analyze/scenario/agente-manipulado").status_code == 401
    assert anonymous.post("/analyze/scenario/agente-manipulado", headers=auth()).status_code == 403
    result = anonymous.post("/analyze/scenario/agente-manipulado", headers=auth("agent-wallet")).json()
    assert result["verdict"] == "BLOCK"
    assert anonymous.get(f"/analyses/{result['analysis_id']}", headers=auth()).status_code == 404
    assert anonymous.get("/analyses", headers=auth()).json() == []
    assert len(anonymous.get("/analyses", headers=auth("agent-wallet")).json()) == 1
    assert anonymous.put("/policies/agent-wallet", json=db.get_policy("agent-wallet"), headers=auth()).status_code == 403


def test_disabling_demo_restores_auth_for_existing_records(anonymous, monkeypatch):
    monkeypatch.setenv("SIGNGUARD_DEMO_MODE", "1")
    result = anonymous.post("/analyze/scenario/agente-manipulado").json()
    monkeypatch.setenv("SIGNGUARD_DEMO_MODE", "0")
    assert anonymous.get("/analyses").status_code == 401
    assert anonymous.get(f"/analyses/{result['analysis_id']}", headers=auth()).status_code == 404
    assert anonymous.get(f"/analyses/{result['analysis_id']}", headers=auth("agent-wallet")).status_code == 200


def test_demo_and_offline_are_independent(anonymous, monkeypatch):
    monkeypatch.setenv("SIGNGUARD_DEMO_MODE", "1")
    monkeypatch.setattr(main, "OFFLINE", False)
    calls = []
    def original_adapter(result, target):
        calls.append((result, target))
        return "0xabc", "https://example.test/tx/0xabc", False
    monkeypatch.setattr(main.attest_mod, "attest_onchain", original_adapter)
    result = anonymous.post("/analyze/scenario/swap-legitimo").json()
    response = anonymous.post("/attest", json={"analysis_id": result["analysis_id"]})
    assert response.status_code == 200 and response.json()["mocked"] is False
    assert calls[0][0] == result
    assert calls[0][1] == fixture()["tx"]["to"]
    assert anonymous.get("/health").json()["offline"] is False
