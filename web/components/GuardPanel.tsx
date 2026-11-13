import type { Verdict } from "@/lib/types";

const LABEL = { ALLOW: "🟢 PERMITIR", WARN: "🟡 ALERTAR", BLOCK: "🔴 BLOQUEAR" } as const;

const FOOTER = {
  ALLOW: "O SignGuard liberou: o agente pôde assinar.",
  WARN: "O SignGuard pediu revisão: o agente não assinou.",
  BLOCK: "O agente foi manipulado, mas não tinha poder de assinar sem o SignGuard.",
} as const;

export default function GuardPanel({ v, loading = false }: { v: Verdict | null; loading?: boolean }) {
  if (loading) {
    return (
      <div className="card">
        <span className="pill">SignGuard</span>
        <p>Analisando a transação antes da assinatura…</p>
        <div className="guard-shimmer" />
      </div>
    );
  }
  if (!v) return <div className="card muted">Aguardando o agente montar uma transação…</div>;

  const signed = v.verdict === "ALLOW";
  const risk = Math.min(100, Math.max(0, v.risk_score));

  return (
    <div className={`card verdict-hero ${v.verdict}`}>
      <div className="verdict-top">
        <span className={`badge ${v.verdict}`}>{LABEL[v.verdict]}</span>
        <span className={`sign-state ${signed ? "ok" : "denied"}`}>
          {signed ? "✅ Assinatura liberada" : "🔒 Assinatura negada"}
        </span>
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

      {v.reasons.length > 0 && (
        <ul className="list">
          {v.reasons.map((r, i) => (
            <li key={`${i}-${r}`}>{r}</li>
          ))}
        </ul>
      )}

      <p className="muted small" style={{ marginBottom: 0 }}>
        {FOOTER[v.verdict]}
      </p>
    </div>
  );
}