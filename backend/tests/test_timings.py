"""Contrato de latência existente: LangGraph paralelo, API, SQLite e health."""
from threading import Barrier
from time import sleep

from agents import graph
from api.models import Verdict
from test_backend import client
from test_properties import FX


def test_wrapper_preserva_medicao_interna_e_usa_relogio_monotonico(monkeypatch):
    clock = iter([10.0, 10.025])
    monkeypatch.setattr(graph.time, "perf_counter", lambda: next(clock))
    result = graph._timed("judge", lambda state: {"timings": {"jev": 12}, "verdict": {}})({"t0": 9.8})
    assert result["timings"] == {"jev": 12, "judge": 25, "decision": 225}


def test_total_nao_soma_ramos_paralelos_e_separa_explicacao(monkeypatch):
    # A barreira exige concorrência real do LangGraph. Não substitui seu executor.
    barrier = Barrier(2)

    def branch(state):
        barrier.wait(timeout=5)
        sleep(0.1)
        return {}

    monkeypatch.setattr(graph, "decoder_node", lambda state: {})
    monkeypatch.setattr(graph, "threat_node", branch)
    monkeypatch.setattr(graph, "policy_node", branch)
    monkeypatch.setattr(graph, "judge_node", lambda state: {"verdict": {"verdict": "ALLOW"}})

    def explain(state):
        sleep(0.06)
        return {}

    monkeypatch.setattr(graph, "explain_node", explain)
    monkeypatch.setattr(graph, "GRAPH", graph.build_graph())
    out = graph.run(FX["swap-legitimo"]["tx"], {})["verdict"]["timings_ms"]
    assert out["threat"] >= 90 and out["policy"] >= 90
    assert out["decision"] < out["threat"] + out["policy"]
    assert out["explain"] >= 50
    assert out["total"] >= out["decision"] + out["explain"] - 2  # arredondamento por nó
    assert out["total"] >= out["decision"]


def test_api_preserva_timings_no_sqlite_e_health(client, monkeypatch):
    monkeypatch.setenv("SIGNGUARD_DEMO_MODE", "1")
    with graph._recent_lock:
        graph._recent_decisions.clear()
    assert client.get("/health").json()["latency_ms"] is None
    result = client.post("/analyze/scenario/swap-legitimo").json()
    validated = Verdict.model_validate(result)
    timings = validated.timings_ms
    assert {"decoder", "threat", "policy", "judge", "decision", "explain", "total"} <= timings.keys()
    assert all(type(value) is int and value >= 0 for value in timings.values())
    assert timings["total"] >= timings["decision"]
    health = client.get("/health").json()
    assert health["ok"] and health["demo_mode"]
    assert health["latency_ms"] == {"last": timings["decision"], "p50": timings["decision"],
                                    "p95": timings["decision"], "n": 1}
    stored = client.get(f"/analyses/{result['analysis_id']}").json()["result"]
    assert stored == result
    assert stored["intent_hash"] == result["intent_hash"] and stored["report_hash"] == result["report_hash"]


def test_health_percentis_e_janela_de_200(monkeypatch):
    from collections import deque
    monkeypatch.setattr(graph, "_recent_decisions", deque(range(1, 201), maxlen=200))
    assert graph.latency_stats() == {"last": 200, "p50": 100, "p95": 190, "n": 200}
