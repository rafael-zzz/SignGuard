# 05 — Backend Schema · SignGuard

## 1. API (FastAPI)
| Método | Rota | Descrição |
|---|---|---|
| POST | `/analyze` | Roda o grafo e retorna veredito |
| POST | `/analyze/scenario/{id}` | Roda um cenário de demo (usa dados da fixture) |
| GET | `/scenarios` | Lista cenários para os botões do front |
| POST | `/attest` | Registra veredito on-chain |
| GET | `/analyses/{id}` | Detalhe de uma análise |
| GET | `/analyses` | Histórico |
| GET/PUT | `/policies/{owner}` | Lê/atualiza política |
| POST | `/forensic` | Relatório pós-incidente (mock) |
| GET | `/health` | Status, classificador (`classifier.enabled`) e `latency_ms` da decisão (última, p50, p95) |

## 2. Modelos (Pydantic)
```python
class TxInput(BaseModel):
    chain_id: int = 1
    from_: str = Field(alias="from")
    to: str
    data: str = "0x"
    value: str = "0"          # wei, string
    context: str | None = None  # texto livre do usuário/bot -> SEMPRE não confiável
    owner_id: str = "default"
    source: Literal["user","agent"] = "user"   # "agent": com contexto e Jev fora -> ALERTAR (fail-closed)

class BalanceChange(BaseModel):
    token: str; symbol: str; delta: str

class Decoded(BaseModel):
    action: Literal["transfer","approve","transferFrom","swap","native_transfer","unknown"]
    token: str | None; spender: str | None; amount: str | None
    is_unlimited: bool = False
    balance_changes: list[BalanceChange] = []
    summary_ptbr: str

class Signal(BaseModel):
    code: str        # ex: CONTRACT_NEW, UNVERIFIED, BLOCKLISTED, UNLIMITED_APPROVAL,
                     #     PROMPT_INJECTION, INTENT_MISMATCH, CLASSIFIER_UNAVAILABLE
    weight: int      # 0-100
    evidence: str    # url ou dado
    sources: list[Literal["rule","classifier"]] = ["rule"]   # determinístico e/ou probabilístico
    probability: float | None = None                          # só em sinal de classificador

class Classifier(BaseModel):   # o que o Jev viu; entra no report_hash (docs/07 §6.4)
    provider: str              # "jev"
    model: str                 # versão fixada: jev-1.14.0
    status: Literal["ok","off","error"]   # off = sem chave/OFFLINE (só regex)
    thresholds: dict[str, float]          # {"injection": 0.90, "intent": 0.70}
    injection_p: float | None             # maior valor de injection_scores
    injection_scores: dict[str, float] | None   # override, impersonation, bypass, drain
    intent: str | None
    intent_confidence: float | None; intent_probabilities: dict[str, float] | None
    error: str | None

class ThreatReport(BaseModel):
    signals: list[Signal]; risk_score: int
    patterns: list[str] = []   # padrões de golpe recuperados (RAG)
    evidence: list[str] = []   # o que o agente consultou, inclusive fontes indisponíveis
    classifier: Classifier | None = None   # None = transação sem contexto

class PolicyResult(BaseModel):
    allowed: bool; violations: list[str]
    warnings: list[str] = []   # regra não conferida (token sem preço x limite em USD) -> ALERTAR

class ReasonDetail(BaseModel):
    text: str
    sources: list[Literal["rule","classifier"]] = ["rule"]   # selo REGRA / CLASSIFICADOR na tela
    probability: float | None = None

class Verdict(BaseModel):
    analysis_id: str
    verdict: Literal["ALLOW","WARN","BLOCK"]   # BLOCK só vem de regra em código
    risk_score: int
    explanation_ptbr: str      # template, ou reescrita pelo LLM depois do veredito
    reasons: list[str]
    reason_details: list[ReasonDetail] = []    # os mesmos motivos, com a origem
    decoded: Decoded; threat: ThreatReport; policy: PolicyResult
    report_hash: str   # keccak256 do JSON canônico (inclui threat.classifier; não inclui a explicação)
    llm_used: bool = False             # o LLM reescreveu a explicação (nunca o veredito)
    timings_ms: dict[str, int] = {}    # decoder, threat, jev, policy, judge, decision, explain, total

# Forense (mock) — POST /forensic
class ForensicRequest(BaseModel):
    tx_hash: str       # 0x + 64 hex

class FundHop(BaseModel):
    step: int; from_: str = Field(alias="from"); from_label: str
    to: str; to_label: str; token: str; amount: str
    tx_hash: str; minutes_after: int

class ForensicReport(BaseModel):
    tx_hash: str
    mocked: bool       # True = rota simulada, não lida da blockchain
    hops: list[FundHop]
    report_md: str
```

## 3. Estado do LangGraph
```python
class SignGuardState(TypedDict):
    tx: TxInput
    policy: dict
    decoded: Decoded | None
    threat: ThreatReport | None
    policy_result: PolicyResult | None
    verdict: Verdict | None    # fechado no judge; o explain só troca explanation_ptbr
    errors: list[str]
    timings: dict[str, int]    # ms por nó; vira Verdict.timings_ms
```
Nós: `decoder` → (`threat` ∥ `policy`) → `judge` → `explain`. Só o `explain` chama LLM.

## 4. Política (JSON)
```json
{
  "max_value_usd": 500,
  "allowlist": ["0x..."],
  "block_unlimited_approvals": true,
  "allowed_hours": [8, 22],
  "min_contract_age_days": 7
}
```
`allowed_hours` é conferido em UTC. Um dado que a regra precisa e não está disponível (valor em USD, idade de um contrato) conta como violação.

## 5. Banco (SQLite)
```sql
CREATE TABLE analyses (
  id TEXT PRIMARY KEY, created_at TEXT, owner_id TEXT,
  tx_json TEXT, verdict TEXT, risk_score INTEGER,
  result_json TEXT, report_hash TEXT
);
CREATE TABLE attestations (
  analysis_id TEXT REFERENCES analyses(id), chain_id INTEGER,
  tx_hash_onchain TEXT, created_at TEXT
);
CREATE TABLE policies (owner_id TEXT PRIMARY KEY, policy_json TEXT, updated_at TEXT);
CREATE TABLE blocklist (address TEXT PRIMARY KEY, label TEXT, source TEXT);
```

## 6. Ferramentas (tools)
| Tool | Assinatura | Fonte |
|---|---|---|
| `simulate_tx` | `(tx) -> balance_changes, trace` | Anvil fork |
| `decode_calldata` | `(to, data) -> fn, args` | ABIs locais + 4byte |
| `contract_info` | `(addr) -> age_days, verified, creator` | Etherscan |
| `check_blocklist` | `(addrs) -> hits` | SQLite |
| `jev.classify` | `(context, acao_real) -> injection_p, injection_scores, intent, intent_confidence` | Jev 1.14 fixado, pela API da TypeSafe ou pelo OpenRouter (`/api/v1/systemone`); sem nenhuma chave → desligado |
| `search_patterns` | `(query) -> docs` | Chroma (em memória) sobre `patterns.json`; sem `chromadb`, tags |
| `trace_funds` | `(tx_hash) -> hops` | mock (rota derivada do hash) |

## 7. Contrato
```solidity
struct Attestation {
    bytes32 intentHash; address target; uint8 verdict;
    uint8 riskScore; bytes32 reportHash; uint64 timestamp; address attester;
}
mapping(bytes32 => Attestation) public attestations;
mapping(address => uint32) public blockCount; // reputação pública por contrato
function isBlocked(bytes32 intentHash) external view returns (bool); // para guards/carteiras vetarem
```
`intentHash` = keccak256(chainId, from, to, value, data) — identifica a intenção antes de existir hash on-chain.

## 8. Estrutura do repositório
```
signguard/
  .env.example
  README.md
  docs/        01..07
  backend/
    api/       main.py, models.py, db.py, attest.py, config.py
    agents/    graph.py, decoder.py, threat.py, policy.py, judge.py, forensic.py, llm.py, prompts.py
    tools/     decode.py, simulate.py, etherscan.py, jev.py, rag.py, trace.py, hashing.py
    data/      patterns.json (+ signguard.db gerado)
    demo/      make_fixtures.py, fixtures/*.json, wallet_bot.py
    eval/      make_dataset.py, dataset.jsonl (60 casos rotulados), results.json, results-live-jev.json
    scripts/   eval.py (evidências), check_llm.py
    tests/     test_scenarios.py, test_agents.py, test_properties.py, test_backend.py
  contracts/   src/SignGuardRegistry.sol, test/, script/Deploy.s.sol
  web/         app/, components/, lib/types.ts, lib/api.ts, mocks/mock-data.json
```
`web/lib/types.ts` espelha `backend/api/models.py`: mudou um, muda o outro.
