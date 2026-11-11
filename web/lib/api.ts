// Cliente da API. Com NEXT_PUBLIC_USE_MOCKS=1 o front funciona sem backend (mocks/mock-data.json).
import mock from "@/mocks/mock-data.json";
import type { AttestResponse, Scenario, TxInput, Verdict } from "./types";

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
