"""Orquestração com LangGraph. Dono: Rafael.
Fluxo (TRD §3): decoder -> (threat ∥ policy) -> judge.
O atestado on-chain é opcional e fica fora do grafo: é disparado por POST /attest (docs/03-app-flow.md)."""
import operator
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from agents.decoder import decoder_node
from agents.judge import judge_node
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
    contracts: dict                  # threat -> judge: contract_info por endereço
    rag_docs: list[dict]             # threat -> judge: padrões de golpe recuperados
    llm_calls: Annotated[list[Any], operator.add]
    llm_seconds: Annotated[float, operator.add]   # tempo de LLM já gasto nesta análise (orçamento do TRD §7)


def build_graph():
    g = StateGraph(SignGuardState)
    g.add_node("decoder", decoder_node)
    g.add_node("threat", threat_node)
    g.add_node("policy", policy_node)
    g.add_node("judge", judge_node)
    g.add_edge(START, "decoder")
    g.add_edge("decoder", "threat")
    g.add_edge("decoder", "policy")
    g.add_edge(["threat", "policy"], "judge")
    g.add_edge("judge", END)
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


def run(tx: dict, policy: dict, offline: dict | None = None) -> dict:
    """Estado final completo (inclui `errors`). Útil para testes e depuração."""
    return GRAPH.invoke({"tx": normalize_tx(tx), "policy": policy, "offline": offline,
                         "llm_calls": [], "llm_seconds": 0.0, "errors": []})


def analyze(tx: dict, policy: dict, offline: dict | None = None) -> dict:
    return run(tx, policy, offline)["verdict"]
