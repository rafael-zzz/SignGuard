"""Compatibilidade da parte de Dávila com interfaces originais de Rafael e Davi."""
import json

import pytest

from agents.graph import analyze
from api import db, main
from api.config import FIXTURES_DIR
from tools.decode import decode_calldata
from tools.simulate import simulate_tx
from test_backend import client


def fixture(name="swap-legitimo"):
    return json.loads((FIXTURES_DIR / f"{name}.json").read_text())


def test_api_rejects_other_chains_before_original_decoder(client, monkeypatch):
    tx = fixture()["tx"]
    tx["chain_id"] = 137
    monkeypatch.setattr(main, "analyze", lambda *a: pytest.fail("rede inválida chegou ao grafo"))
    response = client.post("/analyze", json=tx)
    assert response.status_code == 422
    assert client.get("/analyses").json() == []


def test_api_passes_original_graph_inputs_and_preserves_verdict(client, monkeypatch):
    fx = fixture()
    policy = db.get_policy("default")
    result = analyze(fx["tx"], policy, fx["offline"])
    received = []
    def original_interface(tx_arg, policy_arg, offline_arg=None):
        received.append((tx_arg, policy_arg, offline_arg))
        return result
    monkeypatch.setattr(main, "analyze", original_interface)
    response = client.post("/analyze/scenario/swap-legitimo")
    assert received == [(fx["tx"], policy, fx["offline"])]
    assert response.json() == result
    assert db.get_analysis(result["analysis_id"])["result"] == result


@pytest.mark.parametrize("scenario", ["approve-golpe", "swap-legitimo", "endereco-suspeito", "agente-manipulado"])
def test_tools_support_original_agent_call_signatures(scenario):
    fx = fixture(scenario)
    tx = fx["tx"]
    decoded = decode_calldata(tx["to"], tx["data"], tx["value"])
    assert {"action", "function", "token", "token_symbol", "spender", "recipient", "amount", "amount_usd", "is_unlimited"} <= decoded.keys()
    simulation = simulate_tx(tx, decoded, fx["offline"])
    assert simulation["ok"] is True
    assert simulation["balance_changes"] == fx["offline"]["balance_changes"]


@pytest.mark.parametrize("error", [RuntimeError("private details"), TimeoutError("private provider")])
def test_api_handles_errors_from_original_attester(client, monkeypatch, error):
    result = client.post("/analyze/scenario/swap-legitimo").json()
    monkeypatch.setattr(main, "OFFLINE", False)
    def failed(result_arg, target):
        assert result_arg == result
        assert target == fixture()["tx"]["to"]
        raise error
    monkeypatch.setattr(main.attest_mod, "attest_onchain", failed)
    response = client.post("/attest", json={"analysis_id": result["analysis_id"]})
    assert response.status_code == 502
    assert "private" not in response.text
    with db.conn() as c:
        assert c.execute("SELECT COUNT(*) FROM attestations").fetchone()[0] == 0


def test_original_attester_mock_without_configuration_is_preserved(client, monkeypatch):
    result = client.post("/analyze/scenario/swap-legitimo").json()
    monkeypatch.setattr(main, "OFFLINE", False)
    monkeypatch.setattr(main.attest_mod, "configured", lambda: False)
    response = client.post("/attest", json={"analysis_id": result["analysis_id"]})
    assert response.json() == {"analysis_id": result["analysis_id"], "onchain_tx": None, "explorer_url": None, "mocked": True}
    with db.conn() as c:
        assert c.execute("SELECT COUNT(*) FROM attestations").fetchone()[0] == 0


def test_job_storage_is_available_but_not_wired_into_original_attester(client):
    result = client.post("/analyze/scenario/swap-legitimo").json()
    registry = "0x" + "1" * 40
    row, created = db.claim_attestation(result, 11155111, registry)
    assert created and row["status"] == "reserved"
    again, created = db.claim_attestation(result, 11155111, registry)
    assert not created and again == row
    db.update_attestation_job(result, 11155111, registry, "pending", "0xabc")
    row, created = db.claim_attestation(result, 11155111, registry)
    assert not created and row["tx_hash"] == "0xabc" and row["status"] == "pending"
    # O endpoint offline não alega que há proteção/coordenação do adapter com esta tabela.
    assert client.post("/attest", json={"analysis_id": result["analysis_id"]}).json()["mocked"]
    unchanged, _ = db.claim_attestation(result, 11155111, registry)
    assert unchanged == row
