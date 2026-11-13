"use client";
import clsx from "clsx";
import { ShieldCheck } from "lucide-react";
import type { Verdict } from "@/lib/types";
import { Card, shortenAddrs, verdictMap } from "./ui";

export default function GuardPanel({ v }: { v: Verdict | null }) {
  if (!v)
    return (
      <Card className="flex items-center gap-3 text-body-sm text-text-secondary">
        <ShieldCheck size={16} /> Aguardando o agente montar uma transação…
      </Card>
    );
  const vm = verdictMap[v.verdict];
  const signed = v.verdict === "ALLOW";
  return (
    <Card>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <span className={clsx("inline-flex items-center gap-2 text-amount font-semibold", vm.text)}>
          <span className={clsx("size-2.5 rounded-full", vm.bg)} /> {vm.label}
        </span>
        <span className="tabular shrink-0 text-body font-medium text-text-tertiary">{v.risk_score}/100</span>
      </div>
      <p className="mt-3 text-body font-medium">{shortenAddrs(v.explanation_ptbr)}</p>
      <p className="mt-2 text-caption text-text-tertiary">
        {signed
          ? "O agente foi autorizado a assinar."
          : "O agente foi manipulado, mas não tinha poder de assinar sem o SignGuard."}
      </p>
    </Card>
  );
}
