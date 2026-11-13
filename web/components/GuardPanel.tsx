"use client";
import clsx from "clsx";
import { Lock, ShieldCheck, Unlock } from "lucide-react";
import type { Verdict } from "@/lib/types";
import { Card, Overline, shortenAddrs, verdictMap } from "./ui";

const FOOTER = {
  ALLOW: "O SignGuard liberou: o agente pôde assinar.",
  WARN: "O SignGuard pediu revisão: o agente não assinou.",
  BLOCK: "O SignGuard bloqueou: o agente não assinou.",
} as const;
const MANIPULATED = "O agente foi manipulado, mas não tinha poder de assinar sem o SignGuard.";

export default function GuardPanel({ v, loading = false }: { v: Verdict | null; loading?: boolean }) {
  if (loading) {
    return (
      <Card>
        <p className="flex items-center gap-2 text-body-sm font-medium">
          <ShieldCheck size={16} /> Analisando a transação antes da assinatura…
        </p>
        <div className="mt-4 h-1.5 animate-pulse rounded-full bg-paper-100" />
      </Card>
    );
  }
  if (!v)
    return (
      <Card className="flex items-center gap-3 text-body-sm text-text-secondary">
        <ShieldCheck size={16} className="shrink-0" /> Aguardando o agente montar uma transação…
      </Card>
    );

  const vm = verdictMap[v.verdict];
  const signed = v.verdict === "ALLOW";
  const risk = Math.min(100, Math.max(0, v.risk_score));
  const manipulated = !signed && v.threat.signals.some((s) => s.code === "PROMPT_INJECTION");

  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className={clsx("inline-flex items-center gap-2 text-amount font-semibold", vm.text)}>
          <span className={clsx("size-2.5 rounded-full", vm.bg)} /> {vm.label}
        </span>
        <span className={clsx("inline-flex items-center gap-1.5 text-caption font-semibold", signed ? "text-positive" : "text-text-primary")}>
          {signed ? <Unlock size={14} /> : <Lock size={14} />}
          {signed ? "Assinatura liberada" : "Assinatura negada"}
        </span>
      </div>

      <div className="mt-4">
        <div className="mb-2 flex items-baseline justify-between">
          <span className="text-body-sm text-text-secondary">Nível de risco</span>
          <span className="tabular text-heading font-semibold">
            {v.risk_score}
            <span className="text-caption font-medium text-text-tertiary">/100</span>
          </span>
        </div>
        <div
          className="h-1.5 overflow-hidden rounded-full bg-paper-100"
          role="progressbar"
          aria-label="Nível de risco"
          aria-valuenow={v.risk_score}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <span className={clsx("block h-full animate-grow rounded-full", vm.bg)} style={{ ["--w" as string]: `${risk}%` }} />
        </div>
      </div>

      <p className="mt-4 text-body font-medium">{shortenAddrs(v.explanation_ptbr)}</p>

      {v.reasons.length > 0 && (
        <>
          <Overline className="mt-4">Motivos</Overline>
          <ul className="grid gap-1.5 text-body-sm">
            {v.reasons.map((r, i) => (
              <li key={`${i}-${r}`} className="flex gap-2">
                <span className="mt-1.5 size-1 shrink-0 rounded-full bg-text-primary" />
                <span className="min-w-0 [overflow-wrap:anywhere]">{shortenAddrs(r)}</span>
              </li>
            ))}
          </ul>
        </>
      )}

      <p className="mt-4 text-caption text-text-tertiary">{manipulated ? MANIPULATED : FOOTER[v.verdict]}</p>
    </Card>
  );
}
