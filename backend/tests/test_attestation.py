"""Web3 controlado: receipt, reenvio, falha, rede errada e sobrescrita."""
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import web3
from web3.exceptions import TimeExhausted

from api import attest, db, main
from test_backend import client

# Requisitos para Davi: continuam executando/falhando na suíte completa.
pytestmark = pytest.mark.dependency_davi


@pytest.fixture
def chain(client, monkeypatch):
    result = client.post("/analyze/scenario/swap-legitimo").json()
    registry = "0x" + "1" * 40
    sender = "0x" + "2" * 40
    target = db.get_analysis(result["analysis_id"])["tx"]["to"]
    real_web3 = web3.Web3
    w3 = MagicMock()
    w3.eth.chain_id = 11155111
    w3.eth.get_code.return_value = b"\x60\x00"
    account = SimpleNamespace(address=sender, sign_transaction=MagicMock(return_value=SimpleNamespace(raw_transaction=b"signed")))
    w3.eth.account.from_key.return_value = account
    w3.keccak = real_web3.keccak
    h = real_web3.keccak(b"signed")
    contract = w3.eth.contract.return_value
    empty = (bytes(32), "0x" + "0" * 40, 0, 0, bytes(32), 0, "0x" + "0" * 40)
    recorded = (bytes.fromhex(result["intent_hash"][2:]), target, 0, result["risk_score"],
                bytes.fromhex(result["report_hash"][2:]), 123, sender)
    state = {"record": empty}
    contract.functions.getAttestation.return_value.call.side_effect = lambda: state["record"]
    def send(raw):
        state["record"] = recorded
        return h
    w3.eth.send_raw_transaction.side_effect = send
    receipt = {"status": 1, "transactionHash": h, "to": registry, "blockNumber": 123, "from": sender}
    w3.eth.wait_for_transaction_receipt.return_value = receipt
    factory = MagicMock(return_value=w3)
    factory.to_checksum_address = real_web3.to_checksum_address
    monkeypatch.setattr(web3, "Web3", factory)
    monkeypatch.setattr(main, "OFFLINE", False)
    monkeypatch.setattr(attest, "REGISTRY_ADDRESS", registry)
    monkeypatch.setattr(attest, "SEPOLIA_RPC_URL", "http://rpc.test")
    monkeypatch.setattr(attest, "ATTESTER_PRIVATE_KEY", "test-only")
    return SimpleNamespace(result=result, w3=w3, state=state, recorded=recorded, receipt=receipt, target=target)


def job_status():
    with db.conn() as c:
        return c.execute("SELECT status FROM attestation_jobs").fetchone()[0]


def attest_count():
    with db.conn() as c:
        return c.execute("SELECT COUNT(*) FROM attestations").fetchone()[0]


def test_receipt_confirmed_and_retry_idempotent(client, chain):
    body = {"analysis_id": chain.result["analysis_id"]}
    first = client.post("/attest", json=body)
    assert first.status_code == 200, first.text
    assert first.json()["mocked"] is False
    second = client.post("/attest", json=body)
    assert second.json() == first.json()
    assert chain.w3.eth.send_raw_transaction.call_count == 1
    assert attest_count() == 1 and job_status() == "confirmed"
    assert chain.w3.eth.get_transaction_count.call_args.args[1] == "pending"


def test_receipt_timeout_resumes_without_resending(client, chain):
    body = {"analysis_id": chain.result["analysis_id"]}
    chain.w3.eth.wait_for_transaction_receipt.side_effect = [TimeExhausted(), chain.receipt]
    first = client.post("/attest", json=body)
    assert first.status_code == 504
    assert job_status() == "pending" and attest_count() == 0
    assert client.post("/attest", json=body).status_code == 200
    assert chain.w3.eth.send_raw_transaction.call_count == 1
    assert attest_count() == 1


def test_send_timeout_does_not_send_again(client, chain):
    body = {"analysis_id": chain.result["analysis_id"]}
    chain.w3.eth.send_raw_transaction.side_effect = TimeoutError("provider uncertain")
    assert client.post("/attest", json=body).status_code == 504
    chain.state["record"] = chain.recorded  # tx aceita pelo provider antes do timeout
    assert client.post("/attest", json=body).status_code == 200
    assert chain.w3.eth.send_raw_transaction.call_count == 1


def test_receipt_reverted_is_not_saved_as_success(client, chain):
    chain.receipt["status"] = 0
    body = {"analysis_id": chain.result["analysis_id"]}
    assert client.post("/attest", json=body).status_code == 502
    assert job_status() == "failed" and attest_count() == 0
    assert client.post("/attest", json=body).status_code == 409
    assert chain.w3.eth.send_raw_transaction.call_count == 1


def test_existing_registry_record_cannot_be_overwritten(client, chain):
    chain.state["record"] = chain.recorded
    assert client.post("/attest", json={"analysis_id": chain.result["analysis_id"]}).status_code == 409
    chain.w3.eth.send_raw_transaction.assert_not_called()
    assert attest_count() == 0


def test_wrong_chain_or_empty_registry_never_signs(client, chain):
    body = {"analysis_id": chain.result["analysis_id"]}
    chain.w3.eth.chain_id = 1
    assert client.post("/attest", json=body).status_code == 502
    chain.w3.eth.chain_id = 11155111
    chain.w3.eth.get_code.return_value = b""
    assert client.post("/attest", json=body).status_code == 502
    chain.w3.eth.account.from_key.assert_not_called()


def test_different_report_same_intent_conflicts(client, chain):
    body = {"analysis_id": chain.result["analysis_id"]}
    assert client.post("/attest", json=body).status_code == 200
    changed = {**chain.result, "analysis_id": "different", "report_hash": "0x" + "ab" * 32}
    saved = db.get_analysis(chain.result["analysis_id"])
    db.save_analysis(changed, saved["tx"])
    assert client.post("/attest", json={"analysis_id": "different"}).status_code == 409
    assert chain.w3.eth.send_raw_transaction.call_count == 1


def test_wrong_receipt_hash_is_not_confirmed(client, chain):
    chain.receipt["transactionHash"] = bytes(32)
    assert client.post("/attest", json={"analysis_id": chain.result["analysis_id"]}).status_code == 502
    assert attest_count() == 0 and job_status() == "pending"


def test_confirmed_tx_with_wrong_registry_state_is_conflict(client, chain):
    def send(raw):
        chain.state["record"] = (*chain.recorded[:2], 2, *chain.recorded[3:])
        return chain.receipt["transactionHash"]
    chain.w3.eth.send_raw_transaction.side_effect = send
    assert client.post("/attest", json={"analysis_id": chain.result["analysis_id"]}).status_code == 409
    assert attest_count() == 0


def test_pending_hash_is_saved_before_send(client, chain):
    observed = []
    previous_send = chain.w3.eth.send_raw_transaction.side_effect
    def inspect_before_send(raw):
        with db.conn() as c:
            row = c.execute("SELECT status,tx_hash FROM attestation_jobs").fetchone()
            observed.append(dict(row) if row else None)
        return previous_send(raw)
    chain.w3.eth.send_raw_transaction.side_effect = inspect_before_send
    response = client.post("/attest", json={"analysis_id": chain.result["analysis_id"]})
    assert response.status_code == 200
    assert observed and observed[0] is not None, "hash ainda não estava durável no momento do envio"
    assert observed[0]["status"] == "pending"
    assert observed[0]["tx_hash"] == "0x" + bytes(chain.receipt["transactionHash"]).hex()
