import clsx from "clsx";
import type { Verdict } from "@/lib/types";

type Change = Verdict["decoded"]["balance_changes"][number];

// Regra do DS: entrada em verde, saída em preto (nunca vermelho).
export default function BalanceChanges({ changes }: { changes: Change[] }) {
  if (!changes.length) return null;
  return (
    <div className="mt-3">
      <p className="mb-1 text-overline font-semibold uppercase text-text-tertiary">Mudanças de saldo</p>
      {changes.map((b, i) => {
        const neg = String(b.delta).trim().startsWith("-");
        return (
          <div key={i} className="flex items-center gap-3 py-2">
            <div className="grid size-7 shrink-0 place-items-center rounded-full bg-paper-100 text-micro font-semibold">
              {b.symbol.slice(0, 1)}
            </div>
            <span className="min-w-0 flex-1 truncate text-body font-medium">{b.symbol}</span>
            <span className={clsx("tabular min-w-0 break-all text-right text-body font-medium", !neg && "text-positive")}>{b.delta}</span>
          </div>
        );
      })}
    </div>
  );
}
