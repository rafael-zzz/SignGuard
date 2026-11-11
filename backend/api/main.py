"""API do SignGuard. Dono: Dávila.
Rodar (de dentro de backend/):  uvicorn api.main:app --reload --port 8000
Docs interativas: http://localhost:8000/docs"""
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agents import llm
from agents.graph import analyze
from . import attest as attest_mod
from . import db
from .config import FIXTURES_DIR, OFFLINE
from .models import AttestRequest, AttestResponse, TxInput, Verdict

app = FastAPI(title="SignGuard API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
db.init_db()


def _fixtures() -> dict[str, dict]:
    out = {}
    for f in sorted(FIXTURES_DIR.glob("*.json")):
        s = json.loads(f.read_text(encoding="utf-8"))
        out[s["id"]] = s
    return out


@app.get("/health")
def health():
    return {"ok": True, "offline": OFFLINE, "llm": llm.available(), "attest_onchain": attest_mod.configured()}


@app.get("/scenarios")
def scenarios():
    """Cenários de demo para os botões do front."""
    return [{"id": s["id"], "label": s["label"], "expected": s["expected"], "tx": s["tx"]} for s in _fixtures().values()]


@app.post("/analyze", response_model=Verdict)
def analyze_tx(tx: TxInput, scenario_id: str | None = None):
    tx_dict = tx.model_dump(by_alias=True)
    offline = None
    if scenario_id:
        fx = _fixtures().get(scenario_id)
        if not fx:
            raise HTTPException(404, "cenário não encontrado")
        offline = fx.get("offline")
    result = analyze(tx_dict, db.get_policy(tx.owner_id), offline)
    db.save_analysis(result, tx_dict)
    return result


@app.post("/analyze/scenario/{scenario_id}", response_model=Verdict)
def analyze_scenario(scenario_id: str):
    fx = _fixtures().get(scenario_id)
    if not fx:
        raise HTTPException(404, "cenário não encontrado")
    return analyze_tx(TxInput.model_validate(fx["tx"]), scenario_id)


@app.get("/analyses")
def analyses():
    return db.list_analyses()


@app.get("/analyses/{analysis_id}")
def analysis(analysis_id: str):
    a = db.get_analysis(analysis_id)
    if not a:
        raise HTTPException(404, "análise não encontrada")
    return a


@app.get("/policies/{owner_id}")
def get_policy(owner_id: str):
    return db.get_policy(owner_id)


@app.put("/policies/{owner_id}")
def put_policy(owner_id: str, policy: dict):
    db.put_policy(owner_id, policy)
    return db.get_policy(owner_id)


@app.post("/attest", response_model=AttestResponse)
def attest(req: AttestRequest):
    a = db.get_analysis(req.analysis_id)
    if not a:
        raise HTTPException(404, "análise não encontrada")
    res, tx = a["result"], a["tx"]
    target = res["decoded"].get("spender") or res["decoded"].get("recipient") or tx["to"]
    try:
        h, url, mocked = attest_mod.attest_onchain(res, target)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"falha ao registrar on-chain: {e}") from e
    db.save_attestation(req.analysis_id, 11155111, h)
    return AttestResponse(analysis_id=req.analysis_id, onchain_tx=h, explorer_url=url, mocked=mocked)


@app.post("/forensic")
def forensic(body: dict):
    """Mock do Agente Forense (fora do MVP)."""
    tx_hash = body.get("tx_hash", "0x…")
    return {
        "tx_hash": tx_hash,
        "report_md": (
            f"# Relatório forense (demo)\n\n- Transação analisada: `{tx_hash}`\n"
            "- Rota dos fundos: carteira da vítima → endereço do golpista → mixer/bridge (rastreamento completo no roadmap)\n"
            "- Próximos passos: acionar a exchange de destino com este relatório e registrar boletim de ocorrência.\n"
        ),
    }
