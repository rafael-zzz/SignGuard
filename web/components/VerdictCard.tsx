"use client";
// Tela Resultado (04-design-brief). Dono: Caio.
import { useState } from "react";
import { attest } from "@/lib/api";
import type { Verdict } from "@/lib/types";

const LABEL = { ALLOW: "🟢 PERMITIR", WARN: "🟡 ALERTAR", BLOCK: "🔴 BLOQUEAR" } as const;

export const short = (a?: string | null) => (a && a.length > 12 ? `${a.slice(0, 6)}…${a.slice(-4)}` : a ?? "—");

function CopyBtn({ text }: { text: string }) {
  const [ok, setOk] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setOk(true);
      setTimeout(() => setOk(false), 1200);
    } catch {
      /* clipboard indisponível: ignora */
    }
  }
  return (
    <button type="button" className="copy-btn" onClick={copy} title="Copiar">
      {ok ? "copiado ✓" : "copiar"}
    </button>
  );
}

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

  const sim = v.decoded.simulation_ok;
  const decoderKind = sim === false ? "warn" : "ok";
  const threatKind = v.threat.signals.length === 0 ? "ok" : v.threat.risk_score >= 40 ? "block" : "warn";

  return (
    <div className="grid" style={{ marginTop: 28 }}>
      {/* ---------- Veredito ---------- */}
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
            <span style={{ ["--w" as string]: `${Math.min(100, Math.max(0, v.risk_score))}%` }} />
          </div>
        </div>

        <p className="explanation">{v.explanation_ptbr}</p>
      </div>

      {/* ---------- Agentes ---------- */}
      <div className="grid grid-3">
        <div className="card agent">
          <div className="agent-head">
            <span className="agent-icon">🔎</span>
            <h3>Decodificador</h3>
            <Status kind={decoderKind}>{sim === false ? "reverteu" : "ok"}</Status>
          </div>
          <p>{v.decoded.summary_ptbr}</p>

          {v.decoded.balance_changes.length > 0 && (
            <div className="deltas">
              <span className="muted small">Mudanças de saldo</span>
              {v.decoded.balance_changes.map((b, i) => (
                <div key={i} className="delta-row">
                  <span>{b.symbol}</span>
                  <span className={`mono delta ${String(b.delta).trim().startsWith("-") ? "neg" : "pos"}`}>{b.delta}</span>
                </div>
              ))}
            </div>
          )}

          <div className="agent-foot muted mono">
            simulação: {sim === null ? "não executada" : sim ? "ok" : "reverteu"}
          </div>
        </div>

        <div className="card agent">
          <div className="agent-head">
            <span className="agent-icon">🛡️</span>
            <h3>Ameaças</h3>
            <Status kind={threatKind}>
              {v.threat.signals.length === 0 ? "limpo" : `${v.threat.signals.length} sinal${v.threat.signals.length > 1 ? "is" : ""}`}
            </Status>
          </div>
          {v.threat.signals.length === 0 && <p className="muted">Nenhum sinal de risco.</p>}
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
            <Status kind={v.policy.allowed ? "ok" : "block"}>{v.policy.allowed ? "ok" : "violada"}</Status>
          </div>
          {v.policy.allowed ? (
            <p className="muted">Dentro das regras.</p>
          ) : (
            v.policy.violations.map((x) => (
              <div key={x} className="signal violation">
                {x}
              </div>
            ))
          )}
        </div>
      </div>

      {/* ---------- Atestado ---------- */}
      <div className="card">
        <div className="attest-row">
          <div>
            <h3 style={{ marginBottom: 4 }}>Atestado on-chain</h3>
            <span className="muted small">Registra este veredito de forma pública e auditável.</span>
          </div>
          <button className="btn" onClick={onAttest} disabled={busy}>
            {busy ? "Registrando…" : "Registrar atestado on-chain"}
          </button>
        </div>
        <hr />
        <div className="hash-row">
          <span className="muted small">intent</span>
          <span className="addr">{short(v.intent_hash)}</span>
          {v.intent_hash && <CopyBtn text={v.intent_hash} />}
        </div>
        {att &&
          (att.startsWith("http") ? (
            <p style={{ marginBottom: 0 }}>
              <a href={att} target="_blank" rel="noopener noreferrer" className="explorer-link">
                Ver no explorer ↗
              </a>
            </p>
          ) : (
            <p className="muted" style={{ marginBottom: 0 }}>
              {att}
            </p>
          ))}
      </div>
    </div>
  );
}