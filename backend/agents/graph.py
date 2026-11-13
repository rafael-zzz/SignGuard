"""Orquestração com LangGraph. Dono: Rafael.
Fluxo (TRD §3, docs/07 §2): decoder -> (threat ∥ policy) -> judge -> explain.
Até o `judge` é o caminho da decisão: só código + o classificador Jev (dentro do threat, com teto ALERTAR).
O `explain` (LLM) roda depois do veredito fechado e só troca o texto.
Cada nó é cronometrado: `timings_ms` sai na resposta e alimenta o /health (docs/07 §7).
O atestado on-chain é opcional e fica fora do grafo: é disparado por POST /attest (docs/03-app-flow.md)."""
import operator
import threading
import time
from collections import deque
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from agents.decoder import decoder_node
from agents.judge import explain_node, judge_node
from agents.policy import policy_node
from agents.threat import threat_node


class SignGuardState(TypedDict, total=False):
    # Contrato (docs/05-backend-schema.md §3)
    tx: dict
    policy: dict
    decoded: dict
    threat: dict
    policy_result: dict
    verdict: dict
    errors: Annotated[list[str], operator.add]   # falhas tratadas (LLM fora do schema, API fora…)
    # Apoio interno entre nós (não vai para a API)
    offline: dict | None             # dados de fixture (modo demo/offline)
    simulation: dict                 # decoder -> threat: {ok, detail, attempted, balance_changes_source}
    involved: list[str]              # decoder -> threat: endereços nos argumentos do calldata
    to_contract: str | None          # decoder -> threat: ETH enviado direto a um contrato
    contracts: dict                  # threat -> judge: contract_info por endereço
    rag_docs: list[dict]             # threat -> judge: padrões de golpe recuperados
    t0: float                        # perf_counter do início da análise
    timings: Annotated[dict, operator.or_]        # ms por nó (+ "jev" e "decision")


def _timed(name: str, fn):
    """Cronometra o nó. No `judge`, grava também `decision`: do início da análise até o veredito fechado."""
    def node(state: dict) -> dict:
        started = time.perf_counter()
        out = dict(fn(state))
        done = time.perf_counter()
        timings = {**out.get("timings", {}), name: round((done - started) * 1000)}
        if name == "judge":
            timings["decision"] = round((done - state.get("t0", started)) * 1000)
        out["timings"] = timings
        return out
    return node


def build_graph():
    g = StateGraph(SignGuardState)
    g.add_node("decoder", _timed("decoder", decoder_node))
    g.add_node("threat", _timed("threat", threat_node))
    g.add_node("policy", _timed("policy", policy_node))
    g.add_node("judge", _timed("judge", judge_node))
    g.add_node("explain", _timed("explain", explain_node))
    g.add_edge(START, "decoder")
    g.add_edge("decoder", "threat")
    g.add_edge("decoder", "policy")
    g.add_edge(["threat", "policy"], "judge")
    g.add_edge("judge", "explain")
    g.add_edge("explain", END)
    return g.compile()


GRAPH = build_graph()


def normalize_tx(tx: dict) -> dict:
    """`value` em wei: decimal (contrato da API) ou hex, como sai de carteiras e do JSON-RPC. `data` vazio vira "0x"."""
    tx = dict(tx)
    raw = str(tx.get("value") or "0").strip().lower()
    try:
        value = int(raw, 16) if raw.startswith("0x") and len(raw) > 2 else int(raw.removeprefix("0x") or "0")
    except ValueError:
        raise ValueError(f"value inválido: {tx.get('value')!r} (esperado wei em decimal ou hex)") from None
    if not 0 <= value < 2**256:
        raise ValueError(f"value fora da faixa de uint256: {tx.get('value')!r}")
    tx["value"] = str(value)
    data = str(tx.get("data") or "0x").strip()
    tx["data"] = data if data.lower().startswith("0x") else "0x" + data
    return tx


_recent_decisions: deque[int] = deque(maxlen=200)   # ms até o veredito, das últimas análises (para o /health)
_recent_lock = threading.Lock()


def percentile(values: list[int], q: float) -> int:
    """Percentil por posto mais próximo (nearest-rank)."""
    ordered = sorted(values)
    return ordered[max(0, min(len(ordered) - 1, -(-len(ordered) * q // 100) - 1))] if ordered else 0


def latency_stats() -> dict | None:
    """Latência da decisão medida neste processo: última, p50 e p95."""
    with _recent_lock:
        values = list(_recent_decisions)
    if not values:
        return None
    return {"last": values[-1], "p50": percentile(values, 50), "p95": percentile(values, 95), "n": len(values)}


def run(tx: dict, policy: dict, offline: dict | None = None) -> dict:
    """Estado final completo (inclui `errors`). Útil para testes e depuração."""
    t0 = time.perf_counter()
    out = GRAPH.invoke({"tx": normalize_tx(tx), "policy": policy, "offline": offline,
                        "t0": t0, "timings": {}, "errors": []})
    timings = {**out["timings"], "total": round((time.perf_counter() - t0) * 1000)}
    out["verdict"] = {**out["verdict"], "timings_ms": timings}
    with _recent_lock:
        _recent_decisions.append(timings["decision"])
    return out


def analyze(tx: dict, policy: dict, offline: dict | None = None) -> dict:
    return run(tx, policy, offline)["verdict"]
