"""Contrato de dados entre agentes, API e front. Mudou aqui -> avise o time (web/lib/types.ts espelha isto)."""
from typing import Annotated, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator


Address = Annotated[str, Field(pattern=r"^0x[0-9a-fA-F]{40}$")]


class TxInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    chain_id: int = Field(default=1, gt=0, lt=2**256, strict=True)
    from_: Address = Field(alias="from")
    to: Address
    data: str = Field(default="0x", pattern=r"^0x(?:[0-9a-fA-F]{2})*$")
    value: str = Field(default="0", pattern=r"^(0|[1-9][0-9]*)$")                 # wei, em string
    context: str | None = None       # texto livre do usuário/bot -> SEMPRE não confiável
    owner_id: str = Field(default="default", min_length=1, max_length=128)        # de quem é a política aplicada

    @field_validator("value")
    @classmethod
    def uint256_value(cls, value: str) -> str:
        if len(value) > 78 or int(value) >= 2**256:
            raise ValueError("value deve caber em uint256")
        return value


class PolicyInput(BaseModel):
    """PUT substitui a política completa; campos ausentes não removem vetos."""
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    max_value_usd: float = Field(ge=0)
    allowlist: list[Address]
    block_unlimited_approvals: bool = Field(strict=True)
    allowed_hours: list[Annotated[int, Field(strict=True, ge=0, le=24)]] = Field(min_length=2, max_length=2)
    min_contract_age_days: int = Field(ge=0, strict=True)

    @field_validator("allowed_hours")
    @classmethod
    def valid_hours(cls, hours: list[int]) -> list[int]:
        if not 0 <= hours[0] < hours[1] <= 24:
            raise ValueError("horário deve satisfazer 0 <= início < fim <= 24")
        return hours


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


class ForensicRequest(BaseModel):
    tx_hash: str = Field(pattern=r"^0x[0-9a-fA-F]{64}$")


class FundHop(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    step: int
    from_: str = Field(alias="from")
    from_label: str
    to: str
    to_label: str
    token: str
    amount: str                      # unidades humanas
    tx_hash: str
    minutes_after: int               # minutos depois da transação do incidente


class ForensicReport(BaseModel):
    tx_hash: str
    mocked: bool                     # True = rota simulada (MVP), não lida da blockchain
    hops: list[FundHop]
    report_md: str


class AttestRequest(BaseModel):
    analysis_id: str


class AttestResponse(BaseModel):
    analysis_id: str
    onchain_tx: str | None
    explorer_url: str | None
    mocked: bool
