// Espelho de backend/api/models.py. Mudou lá -> muda aqui.
export type VerdictCode = "ALLOW" | "WARN" | "BLOCK";

export interface TxInput {
  chain_id: number;
  from: string;
  to: string;
  data: string;
  value: string;
  context?: string | null;
  owner_id: string;
  /** Quem montou a transação. "agent": com contexto e classificador fora, não há PERMITIR. */
  source?: "user" | "agent";
}

export interface BalanceChange { token: string; symbol: string; delta: string }

export interface Decoded {
  action: "transfer" | "approve" | "transferFrom" | "swap" | "native_transfer" | "unknown";
  function: string | null;
  token: string | null;
  token_symbol: string | null;
  spender: string | null;
  recipient: string | null;
  amount: string | null;
  amount_usd: number | null;
  is_unlimited: boolean;
  simulation_ok: boolean | null;
  balance_changes: BalanceChange[];
  summary_ptbr: string;
}

/** "rule" = determinístico (código) · "classifier" = probabilístico (Jev, com probabilidade). */
export type Source = "rule" | "classifier";
export interface Signal { code: string; weight: number; evidence: string; sources?: Source[]; probability?: number | null }
/** O que a camada probabilística viu. Entra no report_hash atestado. */
export interface Classifier {
  provider: string;
  model: string;
  status: "ok" | "off" | "error";
  thresholds: Record<string, number>;
  injection_p?: number | null;
  intent?: "consistente" | "divergente" | "sem_intencao" | null;
  intent_confidence?: number | null;
  intent_probabilities?: Record<string, number> | null;
  error?: string | null;
}
export interface ThreatReport {
  signals: Signal[];
  risk_score: number;
  patterns: string[];
  evidence?: string[];
  classifier?: Classifier | null;
}
export interface ReasonDetail { text: string; sources?: Source[]; probability?: number | null }
export interface PolicyResult { allowed: boolean; violations: string[]; warnings?: string[] }

export interface Verdict {
  analysis_id: string;
  verdict: VerdictCode;
  risk_score: number;
  explanation_ptbr: string;
  reasons: string[];
  /** Mesmos motivos de `reasons`, com a origem de cada um (selo REGRA / CLASSIFICADOR). */
  reason_details?: ReasonDetail[];
  decoded: Decoded;
  threat: ThreatReport;
  policy: PolicyResult;
  intent_hash: string;
  report_hash: string;
  /** true = o LLM reescreveu a explicação. Ele nunca altera o veredito. */
  llm_used: boolean;
  /** ms por nó + "jev", "decision" (até o veredito) e "total". */
  timings_ms?: Record<string, number>;
}

export interface Scenario { id: string; label: string; expected: VerdictCode; tx: TxInput }

export interface FundHop {
  step: number;
  from: string;
  from_label: string;
  to: string;
  to_label: string;
  token: string;
  amount: string;
  tx_hash: string;
  minutes_after: number;
}

export interface ForensicReport { tx_hash: string; mocked: boolean; hops: FundHop[]; report_md: string }

export interface AttestResponse {
  analysis_id: string;
  onchain_tx: string | null;
  explorer_url: string | null;
  mocked: boolean;
}

export interface Policy {
  max_value_usd: number;
  allowlist: string[];
  block_unlimited_approvals: boolean;
  allowed_hours: [number, number];
  min_contract_age_days: number;
}

