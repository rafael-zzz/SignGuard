"""Contrato de dados entre agentes, API e front. Mudou aqui -> avise o time (web/lib/types.ts espelha isto)."""
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class TxInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    chain_id: int = 1
    from_: str = Field(alias="from")
    to: str
    data: str = "0x"
    value: str = "0"                 # wei, em string
    context: str | None = None       # texto livre do usuário/bot -> SEMPRE não confiável
    owner_id: str = "default"        # de quem é a política aplicada


class BalanceChange(BaseModel):
    token: str
    symbol: str
    delta: str                       # unidades humanas, ex: "-25000"


class Decoded(BaseModel):
    action: Literal["transfer", "approve", "transferFrom", "swap", "native_transfer", "unknown"]
    function: str | None = None
    token: str | None = None
    token_symbol: str | None = None
    spender: str | None = None
    recipient: str | None = None
    amount: str | None = None        # unidades humanas
    amount_usd: float | None = None
    is_unlimited: bool = False
    simulation_ok: bool | None = None
    balance_changes: list[BalanceChange] = []
    summary_ptbr: str


class Signal(BaseModel):
    code: str                        # CONTRACT_NEW, UNVERIFIED, BLOCKLISTED, UNLIMITED_APPROVAL, ...
    weight: int                      # 0-100
    evidence: str


class ThreatReport(BaseModel):
    signals: list[Signal] = []
    risk_score: int = 0
    patterns: list[str] = []         # padrões de golpe recuperados (RAG)
    evidence: list[str] = []         # o que o agente consultou (TRD §3), inclusive fontes indisponíveis


class PolicyResult(BaseModel):
    allowed: bool
    violations: list[str] = []


class Verdict(BaseModel):
    analysis_id: str
    verdict: Literal["ALLOW", "WARN", "BLOCK"]
    risk_score: int
    explanation_ptbr: str
    reasons: list[str]
    decoded: Decoded
    threat: ThreatReport
    policy: PolicyResult
    intent_hash: str                 # keccak256(abi.encode(chainId, from, to, value, data))
    report_hash: str                 # keccak256 do JSON canônico do relatório
    llm_used: bool = False


class AttestRequest(BaseModel):
    analysis_id: str


class AttestResponse(BaseModel):
    analysis_id: str
    onchain_tx: str | None
    explorer_url: str | None
    mocked: bool
