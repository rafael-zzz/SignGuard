"use client";
// Tela Resultado (04-design-brief + design-system.md). Dono: Caio.
// Regra do DS: cor só no status (verde/âmbar/vermelho). Todo o resto preto/branco.
import clsx from "clsx";
import { ArrowUpRight, ClipboardList, ScanSearch, ShieldAlert, type LucideIcon } from "lucide-react";
import type { Verdict } from "@/lib/types";
import AttestButton from "./AttestButton";
import BalanceChanges from "./BalanceChanges";
import { AnalysisTime, Card, DetailRow, Hash, Overline, Reasons, SourceBadges, StatusText, shortenAddrs, verdictMap } from "./ui";

export { short } from "./AddressChip"; // mantém imports antigos funcionando

type Tone = "ok" | "warn" | "block" | "neutral";
const dotCls: Record<Tone, string> = {
  ok: "bg-positive", warn: "bg-warning", block: "bg-negative", neutral: "bg-on-dark-subtle",
};

function AgentCard({ icon: Icon, title, tone, status, children }: {
  icon: LucideIcon; title: string; tone: Tone; status: string; children: React.ReactNode;
}) {
  return (
    <Card className="flex flex-col">
      <div className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-1">
        <div className="grid size-9 shrink-0 place-items-center rounded-full bg-paper-100">
          <Icon size={16} />
        </div>
        <h3 className="min-w-0 flex-1 text-heading font-semibold tracking-tight">{title}</h3>
        <StatusText tone={tone}>{status}</StatusText>
      </div>
      <div className="flex flex-1 flex-col text-body-sm text-text-primary">{children}</div>
    </Card>
  );
}

function Evidence({ text }: { text: string }) {
  return text.startsWith("http") ? (
    <a href={text} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-0.5 font-semibold text-text-primary underline-offset-2 hover:underline">
      ver evidência <ArrowUpRight size={12} />
    </a>
  ) : (
    <span className="text-text-secondary [overflow-wrap:anywhere]">{shortenAddrs(text)}</span>
  );
}

export default function VerdictCard({ v }: { v: Verdict }) {
  const sim = v.decoded.simulation_ok;
  const policyWarnings = v.policy.warnings ?? [];
  const nSignals = v.threat.signals.length;
  const threatTone: Tone = nSignals === 0 ? "ok" : v.threat.risk_score >= 40 ? "block" : "warn";
  const decoderTone: Tone = sim === false ? "warn" : "ok";
  const policyTone: Tone = !v.policy.allowed ? "block" : policyWarnings.length ? "warn" : "ok";
  const classifier = v.threat.classifier;
  const p2 = (n?: number | null) => (n == null ? "—" : n.toFixed(2).replace(".", ","));
  const verdictTone: Tone = v.verdict === "ALLOW" ? "ok" : v.verdict === "WARN" ? "warn" : "block";
  const risk = Math.min(100, Math.max(0, v.risk_score));
  const vm = verdictMap[v.verdict];

  const trail: { label: string; detail: string; tone: Tone }[] = [
    { label: "Decodificador", detail: sim === null ? "sem simulação" : sim ? "simulação ok" : "reverteu", tone: decoderTone },
    { label: "Ameaças", detail: nSignals === 0 ? "limpo" : `${nSignals} sinal${nSignals > 1 ? "is" : ""}`, tone: threatTone },
    { label: "Política", detail: !v.policy.allowed ? "violada" : policyWarnings.length ? "não conferida" : "dentro das regras", tone: policyTone },
    { label: "Veredito", detail: vm.label.toLowerCase(), tone: verdictTone },
  ];

  return (
    <div className="mt-8 grid animate-rise grid-cols-1 gap-6">
      {/* Veredito */}
      <section>
        <Overline>Veredito</Overline>
        <div className="flex flex-wrap items-center gap-3">
          <h2 className={clsx("inline-flex items-center gap-2.5 text-balance font-medium", vm.text)}>
            <span className={clsx("size-3 rounded-full", vm.bg)} />
            {vm.label}
          </h2>
          <span className="rounded-full bg-paper-100 px-2.5 py-1 text-micro font-medium text-text-secondary">
            decidido por regras em código
          </span>
          <AnalysisTime v={v} className="rounded-full bg-paper-100 px-2.5 py-1 text-micro font-medium text-text-secondary" />
        </div>

        <div className="mt-5">
          <div className="mb-2 flex items-baseline justify-between">
            <span className="text-body-sm text-text-secondary">Nível de risco</span>
            <span className="tabular text-amount font-semibold">
              {v.risk_score}
              <span className="text-body font-medium text-text-tertiary">/100</span>
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

        <p className="mt-5 max-w-[60ch] text-heading font-medium leading-relaxed">{shortenAddrs(v.explanation_ptbr)}</p>
        <p className="mt-1 text-caption text-text-tertiary">
          {v.llm_used ? "Texto escrito por IA depois do veredito; a IA não altera a decisão." : "Texto gerado por template, sem IA."}
        </p>

        {v.reasons.length > 0 && (
          <div className="mt-5 max-w-[70ch]">
            <Overline>Motivos</Overline>
            <Reasons v={v} />
            <p className="mt-3 text-caption text-text-tertiary">
              Só motivo com selo REGRA pode bloquear. O classificador no máximo pede revisão.
            </p>
          </div>
        )}
      </section>

      {/* Trilha dos agentes — card escuro (substitui o "map card" da referência) */}
      <section className="grain overflow-hidden rounded-md bg-ink-950 p-4 text-on-dark">
        <p className="mb-3 text-overline font-semibold uppercase text-on-dark-muted">Trilha dos agentes</p>
        <ol className="grid gap-3 sm:grid-cols-4 sm:gap-2">
          {trail.map((s, i) => (
            <li key={s.label} className="flex items-center gap-2.5 sm:flex-col sm:items-start sm:gap-2">
              <div className="flex items-center gap-2 sm:w-full">
                <span className={clsx("size-2 shrink-0 rounded-full", dotCls[s.tone])} />
                {i < trail.length - 1 && <span className="hidden h-px flex-1 bg-ink-border sm:block" />}
              </div>
              <div>
                <p className="text-body-sm font-semibold">{s.label}</p>
                <p className="text-caption text-on-dark-muted">{s.detail}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      {/* Agentes */}
      <section>
        <Overline>Agentes</Overline>
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
          <AgentCard icon={ScanSearch} title="Decodificador" tone={decoderTone} status={sim === false ? "reverteu" : "ok"}>
            <p>{shortenAddrs(v.decoded.summary_ptbr)}</p>
            <BalanceChanges changes={v.decoded.balance_changes} />
            <p className="mt-auto pt-3 text-caption text-text-tertiary">
              simulação: {sim === null ? "não executada" : sim ? "ok" : "reverteu"}
            </p>
          </AgentCard>

          <AgentCard
            icon={ShieldAlert}
            title="Ameaças"
            tone={threatTone}
            status={nSignals === 0 ? "limpo" : `${nSignals} sinal${nSignals > 1 ? "is" : ""}`}
          >
            {nSignals === 0 && <p className="text-text-secondary">Nenhum sinal de risco.</p>}
            {v.threat.signals.map((s) => (
              <div key={s.code} className="py-2 first:pt-0">
                <div className="flex items-center justify-between gap-2">
                  <span className="min-w-0 break-all font-mono text-caption font-semibold">{s.code}</span>
                  <span className="tabular shrink-0 text-caption text-text-tertiary">peso {s.weight}</span>
                </div>
                <div className="mb-1"><SourceBadges sources={s.sources} probability={s.probability} /></div>
                <Evidence text={s.evidence} />
              </div>
            ))}
            {classifier && (
              <p className="tabular pt-3 text-caption text-text-tertiary">
                Classificador {classifier.model}:{" "}
                {classifier.status === "ok"
                  ? `injeção ${p2(classifier.injection_p)} (limiar ${p2(classifier.thresholds.injection)}) · intenção ${classifier.intent ?? "—"} ${p2(classifier.intent_confidence)} (limiar ${p2(classifier.thresholds.intent)})`
                  : classifier.status === "error"
                    ? "não respondeu — contexto checado só por regex"
                    : "desligado — contexto checado só por regex"}
              </p>
            )}
            {v.threat.patterns.length > 0 && (
              <p className="mt-auto pt-3 text-caption text-text-tertiary">Padrões de golpe: {v.threat.patterns.join(", ")}</p>
            )}
          </AgentCard>

          <AgentCard
            icon={ClipboardList}
            title="Política"
            tone={policyTone}
            status={!v.policy.allowed ? "violada" : policyWarnings.length ? "não conferida" : "ok"}
          >
            {v.policy.allowed && !policyWarnings.length && <p className="text-text-secondary">Dentro das regras.</p>}
            {(v.policy.violations.length > 0 || policyWarnings.length > 0) && (
              <ul className="grid gap-2">
                {v.policy.violations.map((x) => (
                  <li key={x} className="flex gap-2">
                    <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-negative" />
                    <span className="min-w-0 [overflow-wrap:anywhere]">{shortenAddrs(x)}</span>
                  </li>
                ))}
                {policyWarnings.map((x) => (
                  <li key={x} className="flex gap-2">
                    <span className={clsx("mt-1.5 size-1.5 shrink-0 rounded-full", dotCls.warn)} />
                    <span className="min-w-0 [overflow-wrap:anywhere]">{shortenAddrs(x)}</span>
                  </li>
                ))}
              </ul>
            )}
          </AgentCard>
        </div>
      </section>

      {/* Atestado */}
      <section>
        <Overline>Atestado on-chain</Overline>
        <Card>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h3 className="text-heading font-semibold tracking-tight">Registrar veredito</h3>
              <p className="text-caption text-text-tertiary">Registra este veredito de forma pública e auditável.</p>
            </div>
            <AttestButton analysisId={v.analysis_id} />
          </div>
          <div className="mt-3">
            <DetailRow label="Intent hash"><Hash value={v.intent_hash} /></DetailRow>
            <DetailRow label="Report hash"><Hash value={v.report_hash} /></DetailRow>
          </div>
        </Card>
      </section>
    </div>
  );
}
