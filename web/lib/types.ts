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

export interface Signal { code: string; weight: number; evidence: string }
export interface ThreatReport { signals: Signal[]; risk_score: number; patterns: string[] }
export interface PolicyResult { allowed: boolean; violations: string[] }

export interface Verdict {
  analysis_id: string;
  verdict: VerdictCode;
  risk_score: number;
  explanation_ptbr: string;
  reasons: string[];
  decoded: Decoded;
  threat: ThreatReport;
  policy: PolicyResult;
  intent_hash: string;
  report_hash: string;
  llm_used: boolean;
}

export interface Scenario { id: string; label: string; expected: VerdictCode; tx: TxInput }

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

export interface ForensicReport { tx_hash: string; report_md: string }
