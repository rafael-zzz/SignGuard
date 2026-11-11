"use client";
// Tela Resultado (04-design-brief). Dono: Caio.
import { useState } from "react";
import { attest } from "@/lib/api";
import type { Verdict } from "@/lib/types";

const LABEL = { ALLOW: "🟢 PERMITIR", WARN: "🟡 ALERTAR", BLOCK: "🔴 BLOQUEAR" } as const;

export const short = (a?: string | null) => (a && a.length > 12 ? `${a.slice(0, 6)}…${a.slice(-4)}` : a ?? "—");

export default function VerdictCard({ v }: { v: Verdict }) {
  const [att, setAtt] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onAttest() {
    setBusy(true);
    try {
      const r = await attest(v.analysis_id);
      setAtt(r.mocked ? "Atestado simulado (configure o contrato no backend)." : r.explorer_url);
    } catch (e) {
      setAtt(`Erro: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid" style={{ marginTop: 24 }}>
      <div className="card">
        <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
          <span className={`badge ${v.verdict}`}>{LABEL[v.verdict]}</span>
          <span className="muted">Risco {v.risk_score}/100 {v.llm_used ? "· IA" : "· regras"}</span>
        </div>
        <p style={{ fontSize: 18, marginBottom: 0 }}>{v.explanation_ptbr}</p>
      </div>

      <div className="grid grid-3">
        <div className="card">
          <h3>Decodificador</h3>
          <p>{v.decoded.summary_ptbr}</p>
          {v.decoded.balance_changes.map((b, i) => (
            <div key={i} className="mono">{b.delta} {b.symbol}</div>
          ))}
          <div className="muted mono" style={{ marginTop: 8 }}>
            simulação: {v.decoded.simulation_ok === null ? "não executada" : v.decoded.simulation_ok ? "ok" : "reverteu"}
          </div>
        </div>
        <div className="card">
          <h3>Ameaças</h3>
          {v.threat.signals.length === 0 && <p className="muted">Nenhum sinal de risco.</p>}
          <ul className="list">
            {v.threat.signals.map((s) => (
              <li key={s.code}><b>{s.code}</b> <span className="muted">— {s.evidence}</span></li>
            ))}
          </ul>
          {v.threat.patterns.length > 0 && <p className="muted">Padrões: {v.threat.patterns.join(", ")}</p>}
        </div>
        <div className="card">
          <h3>Política</h3>
          {v.policy.allowed ? <p className="muted">Dentro das regras.</p> : (
            <ul className="list">{v.policy.violations.map((x) => <li key={x}>{x}</li>)}</ul>
          )}
        </div>
      </div>

      <div className="card">
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <button className="btn" onClick={onAttest} disabled={busy}>
            {busy ? "Registrando…" : "Registrar atestado on-chain"}
          </button>
          <span className="mono muted">intent {short(v.intent_hash)}</span>
        </div>
        {att && (att.startsWith("http") ? <p><a href={att} target="_blank">Ver no explorer ↗</a></p> : <p className="muted">{att}</p>)}
      </div>
    </div>
  );
}
