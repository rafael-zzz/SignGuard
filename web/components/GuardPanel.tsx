import type { Verdict } from "@/lib/types";

const LABEL = { ALLOW: "🟢 PERMITIR", WARN: "🟡 ALERTAR", BLOCK: "🔴 BLOQUEAR" } as const;

export default function GuardPanel({ v }: { v: Verdict | null }) {
  if (!v) return <div className="card muted">Aguardando o agente montar uma transação…</div>;
  const signed = v.verdict === "ALLOW";
  return (
    <div className={`card verdict-hero ${v.verdict}`}>
      <span className={`badge ${v.verdict}`}>{LABEL[v.verdict]}</span>
      <b className="mono">{v.risk_score}/100</b>
      <p className="explanation">{v.explanation_ptbr}</p>
      <p className="muted small">
        {signed
          ? "O agente foi autorizado a assinar."
          : "O agente foi manipulado, mas não tinha poder de assinar sem o SignGuard."}
      </p>
    </div>
  );
}