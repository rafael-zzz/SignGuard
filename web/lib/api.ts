// Cliente da API. Com NEXT_PUBLIC_USE_MOCKS=1 o front funciona sem backend (mocks/mock-data.json).
import mock from "@/mocks/mock-data.json";
import type { AttestResponse, ForensicReport, Policy, Scenario, TxInput, Verdict } from "./types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS === "1";
const mocks = mock as unknown as { scenarios: Scenario[]; verdicts: Record<string, Verdict> };

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!r.ok) throw new Error(`${r.status}: ${await r.text()}`);
  return r.json() as Promise<T>;
}

export async function getScenarios(): Promise<Scenario[]> {
  if (USE_MOCKS) return mocks.scenarios;
  return req<Scenario[]>("/scenarios");
}

export async function analyzeScenario(id: string): Promise<Verdict> {
  if (USE_MOCKS) return mocks.verdicts[id];
  return req<Verdict>(`/analyze/scenario/${id}`, { method: "POST" });
}

export async function analyzeTx(tx: TxInput): Promise<Verdict> {
  if (USE_MOCKS) return mocks.verdicts["approve-golpe"];
  return req<Verdict>("/analyze", { method: "POST", body: JSON.stringify(tx) });
}

export async function attest(analysisId: string): Promise<AttestResponse> {
  if (USE_MOCKS) return { analysis_id: analysisId, onchain_tx: null, explorer_url: null, mocked: true };
  return req<AttestResponse>("/attest", { method: "POST", body: JSON.stringify({ analysis_id: analysisId }) });
}

export const DEFAULT_POLICY: Policy = {
  max_value_usd: 5000,
  allowlist: [],
  block_unlimited_approvals: true,
  allowed_hours: [0, 24],
  min_contract_age_days: 7,
};

export async function getPolicy(owner: string): Promise<Policy> {
  if (USE_MOCKS) {
    try {
      const s = localStorage.getItem(`policy:${owner}`);
      if (s) return JSON.parse(s) as Policy;
    } catch {}
    return DEFAULT_POLICY;
  }
  return req<Policy>(`/policies/${owner}`);
}

export async function savePolicy(owner: string, p: Policy): Promise<Policy> {
  if (USE_MOCKS) {
    try { localStorage.setItem(`policy:${owner}`, JSON.stringify(p)); } catch {}
    return p;
  }
  return req<Policy>(`/policies/${owner}`, { method: "PUT", body: JSON.stringify(p) });
}

export async function getForensic(txHash: string): Promise<ForensicReport> {
  if (USE_MOCKS) {
    return {
      tx_hash: txHash,
      report_md: `# Relatório forense (demo)\n\n**Hash:** ${txHash}\n\n1. Fundos saíram da carteira da vítima.\n2. Passaram por 2 endereços intermediários.\n3. Chegaram a uma exchange.\n\n_Texto pronto para a exchange/BO: solicito o bloqueio dos fundos acima._`,
    };
  }
  return req<ForensicReport>("/forensic", { method: "POST", body: JSON.stringify({ tx_hash: txHash }) });
}