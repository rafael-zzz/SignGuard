"""API do SignGuard. Dono: Dávila.
Rodar (de dentro de backend/):  uvicorn api.main:app --reload --port 8000
Docs interativas: http://localhost:8000/docs"""
import json
from contextlib import asynccontextmanager

from pydantic import ValidationError

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from agents import llm
from agents.forensic import investigate
from agents.graph import analyze
from . import attest as attest_mod
from . import db
from .auth import Owner, require_owner, demo_enabled
from .config import FIXTURES_DIR, OFFLINE
from .models import AttestRequest, AttestResponse, ForensicReport, ForensicRequest, TxInput, Verdict, PolicyInput

@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="SignGuard API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _fixtures() -> dict[str, dict]:
    out = {}
    for f in sorted(FIXTURES_DIR.glob("*.json")):
        s = json.loads(f.read_text(encoding="utf-8"))
        out[s["id"]] = s
    return out


@app.get("/health")
def health():
    return {"ok": True, "offline": OFFLINE, "demo_mode": demo_enabled(), "llm": llm.available(), "attest_onchain": not OFFLINE and attest_mod.configured()}


@app.get("/scenarios")
def scenarios():
    """Cenários de demo para os botões do front."""
    return [{"id": s["id"], "label": s["label"], "expected": s["expected"], "tx": s["tx"]} for s in _fixtures().values()]


@app.post("/analyze", response_model=Verdict)
def analyze_tx(tx: TxInput, owner: Owner, scenario_id: str | None = None):
    require_owner(tx.owner_id, owner)
    # O decoder original não recebe chain_id ao chamar decode_calldata.
    # Rejeitar redes fora do MVP evita aplicar metadados mainnet a outra rede.
    if tx.chain_id != 1:
        raise HTTPException(422, "rede não suportada; o MVP analisa somente chain_id=1")
    tx_dict = tx.model_dump(by_alias=True)
    offline = None
    if scenario_id:
        fx = _fixtures().get(scenario_id)
        if not fx:
            raise HTTPException(404, "cenário não encontrado")
        if tx_dict != TxInput.model_validate(fx["tx"]).model_dump(by_alias=True):
            raise HTTPException(422, "transação difere do cenário solicitado")
        offline = fx.get("offline")
    try:
        policy = PolicyInput.model_validate(db.get_policy(tx.owner_id)).model_dump()
    except ValidationError as e:
        raise HTTPException(503, "política persistida inválida; atualize a política completa") from e
    result = analyze(tx_dict, policy, offline)
    Verdict.model_validate(result)
    db.save_analysis(result, tx_dict)
    return result


@app.post("/analyze/scenario/{scenario_id}", response_model=Verdict)
def analyze_scenario(scenario_id: str, owner: Owner):
    fx = _fixtures().get(scenario_id)
    if not fx:
        raise HTTPException(404, "cenário não encontrado")
    return analyze_tx(TxInput.model_validate(fx["tx"]), owner, scenario_id)


@app.get("/analyses")
def analyses(owner: Owner, limit: int = Query(default=50, ge=1, le=200)):
    return db.list_analyses(limit, owner_id=owner)


@app.get("/analyses/{analysis_id}")
def analysis(analysis_id: str, owner: Owner):
    a = db.get_analysis(analysis_id, owner_id=owner)
    if not a:
        raise HTTPException(404, "análise não encontrada")
    return a


@app.get("/policies/{owner_id}")
def get_policy(owner_id: str, owner: Owner):
    require_owner(owner_id, owner)
    return db.get_policy(owner_id)


@app.put("/policies/{owner_id}")
def put_policy(owner_id: str, policy: PolicyInput, owner: Owner):
    require_owner(owner_id, owner)
    db.put_policy(owner_id, policy.model_dump())
    return db.get_policy(owner_id)


@app.post("/attest", response_model=AttestResponse)
def attest(req: AttestRequest, owner: Owner):
    a = db.get_analysis(req.analysis_id, owner_id=owner)
    if not a:
        raise HTTPException(404, "análise não encontrada")
    res, tx = a["result"], a["tx"]
    decoded = res["decoded"]
    target = (decoded.get("spender") if decoded["action"] == "approve" else
              decoded.get("recipient") if decoded["action"] in {"transfer", "transferFrom", "native_transfer"} else tx["to"]) or tx["to"]
    try:
        h, url, mocked = (None, None, True) if OFFLINE else attest_mod.attest_onchain(res, target)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, "falha ao registrar on-chain") from e
    if not mocked and h:
        db.save_attestation(req.analysis_id, 11155111, h)
    return AttestResponse(analysis_id=req.analysis_id, onchain_tx=h, explorer_url=url, mocked=mocked)


@app.post("/forensic", response_model=ForensicReport, response_model_by_alias=True)
def forensic(req: ForensicRequest, owner: Owner):
    """Agente Forense (mock): rota simulada dos fundos + texto pronto para exchange e boletim de ocorrência."""
    return investigate(req.tx_hash)
