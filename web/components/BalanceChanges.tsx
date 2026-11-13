import type { Verdict } from "@/lib/types";

type Change = Verdict["decoded"]["balance_changes"][number];

export default function BalanceChanges({ changes }: { changes: Change[] }) {
  if (!changes.length) return null;
  return (
    <div className="deltas">
      <span className="muted small">Mudanças de saldo</span>
      {changes.map((b, i) => (
        <div key={i} className="delta-row">
          <span>{b.symbol}</span>
          <span className={`mono delta ${String(b.delta).trim().startsWith("-") ? "neg" : "pos"}`}>{b.delta}</span>
        </div>
      ))}
    </div>
  );
}