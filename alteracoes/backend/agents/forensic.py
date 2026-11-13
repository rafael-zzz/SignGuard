"""Agente Forense (mock). Dono: Rafael.
Contrato (TRD §3): entrada `tx_hash`; ferramenta `trace_funds`; saída: relatório em markdown.
Fluxo 5 (docs/03-app-flow.md): hash de um incidente -> relatório com rota dos fundos, endereços e
texto pronto para a exchange e para o boletim de ocorrência.

Roda fora do grafo de análise (não participa do veredito): trace -> report.
Tudo é código, sem LLM. A rota vem de um mock (tools/trace.py) e o relatório diz isso no topo;
a única consulta real é a blocklist, para marcar endereços já conhecidos."""
import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from api import db
from tools.trace import trace_funds

MOCK_NOTICE = ("Relatório de demonstração: a rota abaixo é **simulada** (gerada a partir do hash informado), "
               "não foi lida da blockchain. Não use este documento como prova.")


class ForensicState(TypedDict, total=False):
    tx_hash: str
    hops: list[dict]
    flagged: dict                # endereço -> rótulo na blocklist
    report_md: str
    errors: Annotated[list[str], operator.add]


def _short(a: str) -> str:
    return f"{a[:6]}…{a[-4:]}"


def trace_node(state: dict) -> dict:
    hops = trace_funds(state["tx_hash"])
    addresses = sorted({h[k] for h in hops for k in ("from", "to")})
    try:
        flagged = {hit["address"].lower(): hit["label"] for hit in db.check_blocklist(addresses)}
    except Exception as e:  # noqa: BLE001
        return {"hops": hops, "flagged": {}, "errors": [f"forensic: blocklist indisponível ({type(e).__name__})"]}
    return {"hops": hops, "flagged": flagged}


def build_report(tx_hash: str, hops: list[dict], flagged: dict) -> str:
    first, ends = hops[0], [h for h in hops if not any(o["from"] == h["to"] for o in hops)]
    labels: dict[str, str] = {}
    for h in hops:
        labels.setdefault(h["from"], h["from_label"])
        labels.setdefault(h["to"], h["to_label"])

    rows = "\n".join(
        f"| {h['step']} | +{h['minutes_after']} min | {h['from_label']} `{_short(h['from'])}` | "
        f"{h['to_label']} `{_short(h['to'])}` | {h['amount']} {h['token']} | `{_short(h['tx_hash'])}` |"
        for h in hops)
    addresses = "\n".join(
        f"- `{a}` — {label}" + (f" · **em blocklist: {flagged[a.lower()]}**" if a.lower() in flagged else "")
        for a, label in labels.items())
    destinations = " e ".join(f"{h['to_label'].lower()} `{h['to']}` ({h['amount']} {h['token']})" for h in ends)
    hashes = "\n".join(f"- `{h['tx_hash']}`" for h in hops)

    return f"""# Relatório forense — SignGuard

> ⚠️ {MOCK_NOTICE}

## Resumo
- Transação analisada: `{tx_hash}`
- Valor desviado: **{first['amount']} {first['token']}**, da {first['from_label'].lower()} `{first['from']}` para `{first['to']}`
- Destino final identificado: {destinations}
- Tempo entre o incidente e o último movimento: {hops[-1]['minutes_after']} minutos

## Rota dos fundos
| # | Quando | De | Para | Valor | Transação |
|---|---|---|---|---|---|
{rows}

## Endereços envolvidos
{addresses}

## Transações
{hashes}

## Próximos passos
1. Enviar o pedido abaixo à exchange de destino o quanto antes: o bloqueio só é possível enquanto o saldo está lá.
2. Registrar boletim de ocorrência com o texto abaixo e anexar este relatório.
3. Guardar as evidências: conversas, site ou link usado, capturas de tela e os hashes das transações.
4. Revogar permissões (approve) que a carteira afetada ainda tenha e mover o saldo restante para uma carteira nova.

## Texto para a exchange
> Assunto: pedido de bloqueio preventivo de fundos de origem ilícita
>
> Fui vítima de golpe em {first['token']}. Os fundos saíram da minha carteira `{first['from']}` na transação `{tx_hash}` e, conforme a rota anexa, chegaram a: {destinations}. Solicito o bloqueio preventivo desses valores, a preservação dos dados cadastrais da conta de destino e a indicação do canal para envio de ordem judicial ou do boletim de ocorrência.

## Texto para o boletim de ocorrência
> Em [data e hora], fui induzido(a) a assinar uma transação em blockchain que transferiu {first['amount']} {first['token']} da minha carteira `{first['from']}` para o endereço `{first['to']}`, controlado por terceiro desconhecido (hash `{tx_hash}`). Em seguida os valores foram repartidos e enviados para: {destinations}. Peço o registro do fato como fraude eletrônica (art. 171, § 2º-A, do Código Penal) e a requisição dos dados de quem recebeu os valores.
"""


def report_node(state: dict) -> dict:
    return {"report_md": build_report(state["tx_hash"], state["hops"], state.get("flagged") or {})}


def build_graph():
    g = StateGraph(ForensicState)
    g.add_node("trace", trace_node)
    g.add_node("report", report_node)
    g.add_edge(START, "trace")
    g.add_edge("trace", "report")
    g.add_edge("report", END)
    return g.compile()


GRAPH = build_graph()


def investigate(tx_hash: str) -> dict:
    """{tx_hash, mocked, hops, report_md}. Levanta ValueError se o hash for inválido."""
    out = GRAPH.invoke({"tx_hash": tx_hash, "errors": []})
    return {"tx_hash": tx_hash, "mocked": True, "hops": out["hops"], "report_md": out["report_md"]}
