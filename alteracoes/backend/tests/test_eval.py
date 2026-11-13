"""Dataset, métricas e replay do avaliador; sem modelos ou serviços externos."""
import json
from copy import deepcopy
from pathlib import Path

import pytest

from agents import llm
from agents.graph import analyze, percentile
from api import db
from eval.dataset import DATASET, categories, load_dataset
from eval.make_dataset import build
from scripts.eval import (classification_metrics, classifier_origin, evaluate, injection_metrics, latency_summary,
                          main, parse_args, prf, record_responses)
from tools import jev
from test_properties import jev_answer

ROWS = load_dataset()


def test_quarenta_casos_e_rotulos_independentes_das_previsoes():
    assert len(ROWS) == 40
    # O gerador define o oráculo pelo envelope de segurança, sem importar agentes.
    assert ROWS == build()
    assert {r["expected"] for r in ROWS} == {"ALLOW", "WARN", "BLOCK"}
    tags = {c for row in ROWS for c in categories(row)}
    assert {"approve_malicioso", "swap_legitimo", "blocklist", "prompt_injection",
            "variacao_de_valor", "spenders_diferentes", "contexto_benigno", "contexto_malicioso",
            "prompt_injection_indireto", "contexto_longo", "funcao_desconhecida", "falha_de_simulacao"} <= tags


@pytest.mark.parametrize("change", ["duplicate", "invalid_label", "missing_state", "invalid_boolean"])
def test_dataset_rejeita_dados_invalidos(tmp_path, change):
    rows = deepcopy(ROWS)
    if change == "duplicate":
        rows[1]["id"] = rows[0]["id"]
    elif change == "invalid_label":
        rows[0]["expected"] = "OK"
    elif change == "missing_state":
        del rows[0]["offline"]["simulation_ok"]
    else:
        rows[0]["injection"] = "false"
    path = tmp_path / "dataset.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows))
    with pytest.raises(ValueError, match=str(path)):
        load_dataset(path)


@pytest.mark.dependency_rafael
@pytest.mark.parametrize("row", ROWS, ids=[r["id"] for r in ROWS])
def test_dataset_vereditos_do_envelope_de_seguranca(row):
    result = analyze(row["tx"], db.DEFAULT_POLICIES[row["tx"]["owner_id"]], row["offline"])
    assert result["verdict"] == row["expected"], (
        f"Rafael: {row['id']}; regra={row['why']}; injection={row['injection']}; "
        f"esperado={row['expected']}, obtido={result['verdict']}")


def test_percentis_por_posto_mais_proximo():
    values = list(range(1, 41))
    assert percentile(values, 50) == 20
    assert percentile(values[::-1], 95) == 38
    assert percentile([3], 95) == 3
    assert percentile([], 95) == 0
    assert latency_summary({"total": [1, 2, 3, 4, 100]}) == {"total": {"n": 5, "p50": 3, "p95": 100}}
    assert prf([])["precision"] is None
    assert prf([(True, True), (False, True), (True, False), (False, False)]) == {
        "n": 4, "tp": 1, "fp": 1, "fn": 1, "tn": 1, "precision": 0.5, "recall": 0.5}


def test_classificacoes_ausentes_nao_sao_negativos():
    rows = [{"id": str(i), "tx": {"context": "texto neutro"}, "injection": y}
            for i, y in enumerate([True, True, False, False])]
    results = [{"threat": {"classifier": {"injection_p": p}}} for p in [0.95, None, 0.1, None]]
    metrics = injection_metrics(rows, results, ["recorded", "unavailable", "real", "error"])
    assert metrics["regex"]["n"] == 4
    assert metrics["regex_plus_jev"]["n"] == 2
    assert metrics["regex_plus_jev"]["fn"] == 0  # caso ausente não vira falso negativo
    assert metrics["regex_on_classified"]["n"] == 2
    assert metrics["regex_plus_jev"]["recall"] == 1
    assert set(metrics["by_origin"]) == {"real", "recorded"}


def test_proveniencia_nao_confunde_fixture_com_live():
    row = {"tx": {"context": "teste"}, "offline": {"jev": jev_answer()}}
    result = {"threat": {"classifier": {"status": "ok"}}}
    assert classifier_origin(row, result, True) == "recorded"
    row["offline"].clear()
    assert classifier_origin(row, result, True) == "real"
    assert classifier_origin(row, result, False) == "unverified"
    result["threat"]["classifier"]["status"] = "off"
    assert classifier_origin(row, result, True) == "unavailable"


def test_comparacao_llm_reutiliza_jev_e_estado(monkeypatch):
    row = deepcopy(next(r for r in ROWS if r["id"] == "swap-legitimo__benigno-swap"))
    calls = []

    def changing_classifier(*args, **kwargs):
        calls.append(1)
        return jev_answer(0.99 if len(calls) == 1 else 0.01)

    monkeypatch.setattr(jev, "enabled", lambda: True)
    monkeypatch.setattr(jev, "classify", changing_classifier)
    original = llm.chat_structured
    summary = evaluate([row], runs=10, live=True)
    assert len(calls) == 1  # 10 repetições e 3 ataques ao LLM usam a mesma resposta
    assert summary["decisions_changed_by_llm"] == []
    assert summary["non_deterministic"] == []
    assert summary["classifier"]["real_cases"] == 1  # transporte é mock apenas neste teste
    assert summary["records"][0]["result"]["verdict"] == "WARN"
    assert llm.chat_structured is original
    assert jev.classify is changing_classifier


def test_fixture_jev_preserva_probabilidade_modelo_e_latencia():
    row = deepcopy(next(r for r in ROWS if r["id"] == "swap-legitimo__benigno-swap"))
    row["offline"]["jev"] = {**jev_answer(0.95, "divergente", 0.9), "latency_ms": 348}
    summary = evaluate([row], runs=2)
    c = summary["classifier"]
    assert (c["recorded_cases"], c["real_cases"], c["coverage"], c["real_coverage"]) == (1, 0, 1, 0)
    assert c["latency_ms_by_origin"]["recorded"]["p50"] == 348
    assert "jev" not in summary["latency_ms"]  # 348 é gravado, não foi medido nesta execução
    result = summary["records"][0]["result"]
    assert result["threat"]["classifier"]["model"] == "jev-1.14.0"
    assert result["threat"]["classifier"]["injection_p"] == 0.95
    assert {s["code"] for s in result["threat"]["signals"]} >= {"PROMPT_INJECTION", "INTENT_MISMATCH"}
    del row["offline"]["jev"]["latency_ms"]
    without_latency = evaluate([row], runs=1)
    assert without_latency["classifier"]["cases_classified"] == 1
    assert without_latency["classifier"]["latency_ms_by_origin"] == {}


def test_erro_jev_e_classificador_ausente_nao_contam_cobertura():
    row = deepcopy(next(r for r in ROWS if r["id"] == "agente-50-fornecedor__benigno-pagamento"))
    row["offline"]["jev"] = {"model": "incompleto"}
    summary = evaluate([row], runs=2)
    assert summary["classifier"]["error_cases"] == 1
    assert summary["classifier"]["cases_classified"] == 0
    assert summary["injection"]["regex_plus_jev"] is None
    assert summary["records"][0]["result"]["verdict"] == "WARN"


def test_cli_exporta_e_sinaliza_falsos_allow_sem_mudar_banco(tmp_path, capsys):
    path = tmp_path / "report.json"
    before = Path(db.DB_PATH).read_bytes()
    exit_code = main(["--runs", "1", "--json", str(path)])
    summary = json.loads(path.read_text())
    assert summary["cases"] == 40
    assert exit_code == (0 if summary["security_passed"] else 1)
    if summary["false_allow_attack"]:
        assert exit_code == 1
    assert summary["classifier"]["real_cases"] == 0
    assert summary["decisions_changed_by_llm"] == []
    assert Path(db.DB_PATH).read_bytes() == before
    assert "Matriz de confusão" in capsys.readouterr().out


def test_falso_allow_de_contexto_tambem_e_ataque():
    rows = [{"id": "injecao", "expected": "WARN", "tx_malicious": False, "injection": True},
            {"id": "bloqueado", "expected": "BLOCK", "tx_malicious": True, "injection": False}]
    metrics = classification_metrics(rows, [{"verdict": "ALLOW"}, {"verdict": "BLOCK"}])
    assert metrics["false_allow_malicious"] == []
    assert metrics["false_allow_attack"] == ["injecao"]
    assert metrics["accuracy"] == 0.5
    assert metrics["confusion"]["WARN"]["ALLOW"] == 1


def test_replay_preserva_ausencia_de_classificacao(monkeypatch):
    row = deepcopy(next(r for r in ROWS if r["id"] == "swap-legitimo__benigno-swap"))
    calls = []

    def varying(*args, **kwargs):
        calls.append(1)
        return None if len(calls) == 1 else jev_answer(1.0)

    monkeypatch.setattr(jev, "classify", varying)
    summary = evaluate([row], runs=3)
    assert len(calls) == 1
    assert summary["classifier"]["cases_classified"] == 0
    assert summary["decisions_changed_by_llm"] == []


def test_restauracao_das_ferramentas_mesmo_quando_execucao_falha(monkeypatch):
    from agents import graph
    original_chat, original_classify = llm.chat_structured, jev.classify

    def fail(*args, **kwargs):
        raise RuntimeError("falha de teste")

    monkeypatch.setattr(graph, "analyze", fail)
    with pytest.raises(RuntimeError, match="falha de teste"):
        evaluate([ROWS[0]])
    assert llm.chat_structured is original_chat
    assert jev.classify is original_classify


def test_gravacao_conserva_latencia_e_nao_grava_resposta_ausente(tmp_path, monkeypatch):
    from api import config
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    monkeypatch.setattr(config, "FIXTURES_DIR", fixtures)
    rows = deepcopy(ROWS[:2])
    classifier = {**jev_answer(), "status": "ok"}
    records = [{"classifier_origin": "real", "result": {
        "threat": {"classifier": classifier}, "timings_ms": {"jev": 123}}},
        {"classifier_origin": "unavailable", "result": {"threat": {"classifier": {"status": "off"}}}}]
    path = tmp_path / "dataset.jsonl"
    counts = record_responses(rows, {"records": records}, path)
    assert counts == {"dataset": 1, "fixtures": 0}
    saved = [json.loads(line) for line in path.read_text().splitlines()]
    assert saved[0]["offline"]["jev"]["latency_ms"] == 123
    assert saved[0]["offline"]["jev_provenance"]["source"] == "live"
    assert "jev" not in saved[1]["offline"]
    assert [r["expected"] for r in saved] == [r["expected"] for r in rows]


@pytest.mark.parametrize("args", [["--runs", "0"], ["--runs", "-1"], ["--record-jev"]])
def test_cli_rejeita_argumentos_invalidos(args):
    with pytest.raises(SystemExit) as exc:
        parse_args(args)
    assert exc.value.code == 2
