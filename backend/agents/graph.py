"""Orquestração com LangGraph. Dono: Rafael.
Fluxo: decoder -> (threat ∥ policy) -> judge."""
import operator
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from agents.decoder import decoder_node
from agents.judge import judge_node
from agents.policy import policy_node
from agents.threat import threat_node


class SignGuardState(TypedDict, total=False):
    tx: dict
    policy: dict
    offline: dict | None             # dados de fixture (modo demo/offline)
    decoded: dict
    threat: dict
    policy_result: dict
    verdict: dict
    llm_calls: Annotated[list[Any], operator.add]
    errors: Annotated[list[str], operator.add]


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


def analyze(tx: dict, policy: dict, offline: dict | None = None) -> dict:
    out = GRAPH.invoke({"tx": tx, "policy": policy, "offline": offline, "llm_calls": [], "errors": []})
    return out["verdict"]
