"use client";
// Tela Resultado (04-design-brief). Dono: Caio.
import type { Verdict } from "@/lib/types";
import AddressChip from "./AddressChip";
import AttestButton from "./AttestButton";
import BalanceChanges from "./BalanceChanges";

export { short } from "./AddressChip"; // mantém imports antigos funcionando

const LABEL = { ALLOW: "🟢 PERMITIR", WARN: "🟡 ALERTAR", BLOCK: "🔴 BLOQUEAR" } as const;

function Status({ kind, children }: { kind: "ok" | "warn" | "block"; children: React.ReactNode }) {
  return <span className={`status ${kind}`}>{children}</span>;
}

function Evidence({ text }: { text: string }) {
  return text.startsWith("http") ? (
    <a href={text} target="_blank" rel="noopener noreferrer" className="muted">
      ver evidência ↗
    </a>
  ) : (
    <span className="muted">{text}</span>
  );
}

export default function VerdictCard({ v }: { v: Verdict }) {
  const sim = v.decoded.simulation_ok;
  const policyWarnings = v.policy.warnings ?? [];
  const nSignals = v.threat.signals.length;
  const threatKind = nSignals === 0 ? "ok" : v.threat.risk_score >= 40 ? "block" : "warn";
  const risk = Math.min(100, Math.max(0, v.risk_score));

  return (
    <div className="grid" style={{ marginTop: 28 }}>
      {/* Veredito */}
      <div className={`card verdict-hero ${v.verdict}`}>
        <div className="verdict-top">
          <span className={`badge ${v.verdict}`}>{LABEL[v.verdict]}</span>
          <span className="pill">{v.llm_used ? "análise com IA" : "análise por regras"}</span>
        </div>
        <div className="score">
          <div className="score-label">
            <span className="muted">Nível de risco</span>
            <b className="mono">{v.risk_score}/100</b>
          </div>
          <div className="meter" role="progressbar" aria-valuenow={v.risk_score} aria-valuemin={0} aria-valuemax={100}>
            <span style={{ ["--w" as string]: `${risk}%` }} />
          </div>
        </div>
        <p className="explanation">{v.explanation_ptbr}</p>
      </div>

      {/* Agentes */}
      <div className="grid grid-3">
        <div className="card agent">
          <div className="agent-head">
            <span className="agent-icon">🔎</span>
            <h3>Decodificador</h3>
            <Status kind={sim === false ? "warn" : "ok"}>{sim === false ? "reverteu" : "ok"}</Status>
          </div>
          <p>{v.decoded.summary_ptbr}</p>
          <BalanceChanges changes={v.decoded.balance_changes} />
          <div className="agent-foot muted mono">
            simulação: {sim === null ? "não executada" : sim ? "ok" : "reverteu"}
          </div>
        </div>

        <div className="card agent">
          <div className="agent-head">
            <span className="agent-icon">🛡️</span>
            <h3>Ameaças</h3>
            <Status kind={threatKind}>
              {nSignals === 0 ? "limpo" : `${nSignals} sinal${nSignals > 1 ? "is" : ""}`}
            </Status>
          </div>
          {nSignals === 0 && <p className="muted">Nenhum sinal de risco.</p>}
          {v.threat.signals.map((s) => (
            <div key={s.code} className="signal">
              <div className="signal-top">
                <span className="signal-code">{s.code}</span>
                <span className="mono muted small">peso {s.weight}</span>
              </div>
              <Evidence text={s.evidence} />
            </div>
          ))}
          {v.threat.patterns.length > 0 && (
            <div className="agent-foot muted small">Padrões de golpe: {v.threat.patterns.join(", ")}</div>
          )}
        </div>

        <div className="card agent">
          <div className="agent-head">
            <span className="agent-icon">📋</span>
            <h3>Política</h3>
            <Status kind={!v.policy.allowed ? "block" : policyWarnings.length ? "warn" : "ok"}>
              {!v.policy.allowed ? "violada" : policyWarnings.length ? "não conferida" : "ok"}
            </Status>
          </div>
          {v.policy.allowed && !policyWarnings.length && <p className="muted">Dentro das regras.</p>}
          {v.policy.violations.map((x) => (
            <div key={x} className="signal violation">{x}</div>
          ))}
          {policyWarnings.map((x) => (
            <div key={x} className="signal">{x}</div>
          ))}
        </div>
      </div>

      {/* Atestado */}
      <div className="card">
        <div className="attest-row">
          <div>
            <h3 style={{ marginBottom: 4 }}>Atestado on-chain</h3>
            <span className="muted small">Registra este veredito de forma pública e auditável.</span>
          </div>
          <AttestButton analysisId={v.analysis_id} />
        </div>
        <hr />
        <div className="hash-row">
          <span className="muted small">intent</span>
          <AddressChip address={v.intent_hash} />
        </div>
      </div>
    </div>
  );
}