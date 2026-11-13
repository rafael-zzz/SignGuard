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
    # Quem montou a transação. "agent": com contexto e classificador fora, não há PERMITIR (docs/07 §3).
    source: Literal["user", "agent"] = "user"
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


Source = Literal["rule", "classifier"]   # "rule" = determinístico (código) · "classifier" = probabilístico (Jev)


class Signal(BaseModel):
    code: str                        # CONTRACT_NEW, UNVERIFIED, BLOCKLISTED, UNLIMITED_APPROVAL, ...
    weight: int = Field(ge=0, le=100)  # 0-100
    evidence: str
    sources: list[Source] = ["rule"]
    probability: float | None = Field(default=None, ge=0, le=1)   # só em sinal de classificador


class Classifier(BaseModel):
    """O que a camada probabilística viu. Entra no report_hash: dá para auditar depois (docs/07 §6.4)."""
    provider: str                    # por onde o Jev foi chamado: "typesafe" (direto) ou "openrouter"
    model: str                       # versão que respondeu: jev-1.14.0 ou typesafe/jev-1.14-20261014
    calibrated: bool = True          # probabilidade calibrada do Jev
    status: Literal["ok", "off", "error"]   # off = sem chave/OFFLINE (só regex) · error = não respondeu
    thresholds: dict[str, float]     # limiares fixos em código: {"injection": 0.80, "intent": 0.70}
    injection_p: float | None = Field(default=None, ge=0, le=1)
    intent: Literal["consistente", "divergente", "sem_intencao"] | None = None
    intent_confidence: float | None = Field(default=None, ge=0, le=1)
    intent_probabilities: dict[str, float] | None = None
    error: str | None = None


class ThreatReport(BaseModel):
    signals: list[Signal] = []
    risk_score: int = Field(default=0, ge=0, le=100)
    patterns: list[str] = []         # padrões de golpe recuperados (RAG)
    evidence: list[str] = []         # o que o agente consultou (TRD §3), inclusive fontes indisponíveis
    classifier: Classifier | None = None   # None = transação sem contexto (o classificador não se aplica)


class PolicyResult(BaseModel):
    allowed: bool
    violations: list[str] = []
    warnings: list[str] = []         # regra que não pôde ser conferida (ex.: token sem preço x limite em USD)


class ReasonDetail(BaseModel):
    text: str
    sources: list[Source] = ["rule"]     # selo na tela: REGRA e/ou CLASSIFICADOR
    probability: float | None = Field(default=None, ge=0, le=1)


class Verdict(BaseModel):
    analysis_id: str
    verdict: Literal["ALLOW", "WARN", "BLOCK"]
    risk_score: int = Field(ge=0, le=100)
    explanation_ptbr: str
    reasons: list[str]
    reason_details: list[ReasonDetail] = []   # mesmos motivos de `reasons`, com a origem de cada um
    decoded: Decoded
    threat: ThreatReport
    policy: PolicyResult
    intent_hash: str                 # keccak256(abi.encode(chainId, from, to, value, data))
    report_hash: str                 # keccak256 do JSON canônico do relatório
    llm_used: bool = False           # True = o LLM reescreveu a explicação (nunca o veredito)
    timings_ms: dict[str, int] = {}  # por nó + "jev", "decision" (até o veredito) e "total"


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
