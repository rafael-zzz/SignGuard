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
| GET | `/health` | Status |

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

class BalanceChange(BaseModel):
    token: str; symbol: str; delta: str

class Decoded(BaseModel):
    action: Literal["transfer","approve","transferFrom","swap","native_transfer","unknown"]
    token: str | None; spender: str | None; amount: str | None
    is_unlimited: bool = False
    balance_changes: list[BalanceChange] = []
    summary_ptbr: str

class Signal(BaseModel):
    code: str        # ex: CONTRACT_NEW, UNVERIFIED, BLOCKLISTED, UNLIMITED_APPROVAL
    weight: int      # 0-100
    evidence: str    # url ou dado

class ThreatReport(BaseModel):
    signals: list[Signal]; risk_score: int
    patterns: list[str] = []   # padrões de golpe recuperados (RAG)
    evidence: list[str] = []   # o que o agente consultou, inclusive fontes indisponíveis

class PolicyResult(BaseModel):
    allowed: bool; violations: list[str]
    warnings: list[str] = []   # regra não conferida (token sem preço x limite em USD) -> ALERTAR

class Verdict(BaseModel):
    analysis_id: str
    verdict: Literal["ALLOW","WARN","BLOCK"]
    risk_score: int
    explanation_ptbr: str
    reasons: list[str]
    decoded: Decoded; threat: ThreatReport; policy: PolicyResult
    report_hash: str   # keccak256 do JSON canônico

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
    verdict: Verdict | None
    errors: list[str]
```

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
  docs/        01..06
  backend/
    api/       main.py, models.py, db.py, attest.py, config.py
    agents/    graph.py, decoder.py, threat.py, policy.py, judge.py, forensic.py, llm.py, prompts.py
    tools/     decode.py, simulate.py, etherscan.py, rag.py, trace.py, hashing.py
    data/      patterns.json (+ signguard.db gerado)
    demo/      make_fixtures.py, fixtures/*.json, wallet_bot.py
    tests/     test_scenarios.py, test_agents.py, test_backend.py
  contracts/   src/SignGuardRegistry.sol, test/, script/Deploy.s.sol
  web/         app/, components/, lib/types.ts, lib/api.ts, mocks/mock-data.json
```
`web/lib/types.ts` espelha `backend/api/models.py`: mudou um, muda o outro.
