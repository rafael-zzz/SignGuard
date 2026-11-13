"use client";
// components/ui.tsx — componentes base do design system (docs/design-system.md)
import { useState } from "react";
import clsx from "clsx";
import {
  ArrowRight, ChevronRight, Search, ListFilter, X, Home, Sparkle, LayoutGrid, Copy, Check, Loader2,
  type LucideIcon,
} from "lucide-react";
import type { VerdictCode } from "@/lib/types";

/* CTA pill (onboarding / superfície escura) */
export function CtaPill({ children, onClick, disabled }: { children: React.ReactNode; onClick?: () => void; disabled?: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="flex h-13 w-full items-center justify-between rounded-full border border-ink-border px-5 text-body font-medium text-on-dark transition hover:bg-white/5 disabled:opacity-40"
    >
      {children}
      <ArrowRight size={18} />
    </button>
  );
}

/* CTA principal na sheet branca: pill preta, texto à esquerda, seta à direita */
export function PrimaryButton({ children, onClick, disabled, loading, className }: {
  children: React.ReactNode; onClick?: () => void; disabled?: boolean; loading?: boolean; className?: string;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={clsx(
        "flex h-13 w-full items-center justify-between rounded-full bg-ink-950 px-5 text-body font-medium text-on-dark transition hover:bg-ink-850 disabled:cursor-not-allowed disabled:opacity-40",
        className,
      )}
    >
      {children}
      {loading ? <Loader2 size={18} className="animate-spin" /> : <ArrowRight size={18} />}
    </button>
  );
}

/* Botão secundário na sheet branca (borda 1px, pill) */
export function OutlineButton({ icon: Icon, children, onClick, disabled }: {
  icon?: LucideIcon; children: React.ReactNode; onClick?: () => void; disabled?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="inline-flex h-10 items-center gap-2 rounded-full border border-paper-border px-4 text-body-sm font-semibold text-text-primary transition hover:bg-paper-100 disabled:cursor-not-allowed disabled:opacity-40"
    >
      {Icon && <Icon size={16} />} {children}
    </button>
  );
}

/* Pill secundário (header escuro) */
export function PillButton({ icon: Icon, children, onClick }: { icon: LucideIcon; children: React.ReactNode; onClick?: () => void }) {
  return (
    <button
      onClick={onClick}
      className="inline-flex h-8 items-center gap-1.5 rounded-full border border-ink-border bg-ink-850 px-3 text-caption font-medium text-on-dark hover:bg-ink-900"
    >
      <Icon size={14} /> {children}
    </button>
  );
}

/* Chip selecionável (sheet branca) */
export function Chip({ active, children, onClick }: { active?: boolean; children: React.ReactNode; onClick?: () => void }) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className={clsx(
        "h-8 rounded-full border px-3 text-caption font-medium transition",
        active
          ? "border-ink-950 bg-ink-950 text-on-dark"
          : "border-paper-border bg-paper text-text-primary hover:bg-paper-100",
      )}
    >
      {children}
    </button>
  );
}

/* Header do usuário */
export function UserHeader({ name, avatar }: { name: string; avatar: string }) {
  return (
    <div className="flex items-center justify-between">
      <button className="flex items-center gap-2 text-body font-medium text-on-dark">
        <img src={avatar} alt="" className="size-7 rounded-full object-cover" />
        {name} <ChevronRight size={14} className="text-on-dark-muted" />
      </button>
      <Search size={20} className="text-on-dark" />
    </div>
  );
}

/* Bottom sheet */
export function Sheet({ title, action, children, className }: {
  title?: string; action?: React.ReactNode; children: React.ReactNode; className?: string;
}) {
  return (
    <section className={clsx("rounded-t-sheet bg-paper px-4 pb-24 pt-2 text-text-primary shadow-sheet sm:px-8", className)}>
      <div className="mx-auto mb-4 h-1 w-9 rounded-full bg-handle" />
      {title && (
        <header className="mb-4 flex items-center justify-between">
          <h2 className="text-title font-semibold tracking-tight">{title}</h2>
          {action ?? <ListFilter size={18} />}
        </header>
      )}
      {children}
    </section>
  );
}

export function Overline({ children, className }: { children: React.ReactNode; className?: string }) {
  return <p className={clsx("mb-2 mt-4 text-overline font-semibold uppercase text-text-tertiary first:mt-0", className)}>{children}</p>;
}

/* Card claro (sem sombra, borda 1px) */
export function Card({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={clsx("animate-rise break-words rounded-lg border border-paper-border bg-paper p-4", className)}>{children}</div>;
}

/* Status (adaptação p/ verificação de assinaturas) */
type Status = "valid" | "invalid" | "pending";
const statusMap: Record<Status, { label: string; cls: string }> = {
  valid: { label: "Válida", cls: "text-positive" },
  invalid: { label: "Inválida", cls: "text-negative" },
  pending: { label: "Em análise", cls: "text-warning" },
};

/* Veredito do SignGuard → cor semântica (única cor permitida na UI) */
export const verdictMap: Record<VerdictCode, { label: string; text: string; bg: string }> = {
  ALLOW: { label: "Permitir", text: "text-positive", bg: "bg-positive" },
  WARN: { label: "Alertar", text: "text-warning", bg: "bg-warning" },
  BLOCK: { label: "Bloquear", text: "text-negative", bg: "bg-negative" },
};

/* Rótulo de status pequeno: ponto colorido + texto */
export function StatusText({ tone, children }: { tone: "ok" | "warn" | "block" | "neutral"; children: React.ReactNode }) {
  const cls = { ok: "text-positive", warn: "text-warning", block: "text-negative", neutral: "text-text-tertiary" }[tone];
  const dot = { ok: "bg-positive", warn: "bg-warning", block: "bg-negative", neutral: "bg-text-tertiary" }[tone];
  return (
    <span className={clsx("inline-flex items-center gap-1.5 text-caption font-semibold", cls)}>
      <span className={clsx("size-1.5 rounded-full", dot)} />
      {children}
    </span>
  );
}

/* Linha de transação */
export function TxRow({ icon, title, subtitle, value, status }: {
  icon: React.ReactNode; title: string; subtitle: string; value?: string; status?: Status;
}) {
  return (
    <div className="flex items-center gap-3 py-2.5">
      <div className="grid size-9 shrink-0 place-items-center overflow-hidden rounded-full bg-paper-100">{icon}</div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-body font-medium">{title}</p>
        <p className="truncate text-caption text-text-tertiary">{subtitle}</p>
      </div>
      {status ? (
        <span className={clsx("text-body font-medium", statusMap[status].cls)}>{statusMap[status].label}</span>
      ) : (
        <span className={clsx("tabular text-body font-medium", value?.startsWith("+") && "text-positive")}>{value}</span>
      )}
    </div>
  );
}

/* Tab bar flutuante */
export function TabBar({ active = 0 }: { active?: number }) {
  const items = [Home, Sparkle, LayoutGrid];
  return (
    <nav className="fixed bottom-4 left-1/2 flex h-10 -translate-x-1/2 items-center gap-5 rounded-full bg-ink-1000 px-5 shadow-float">
      {items.map((Icon, i) => (
        <Icon key={i} size={18} className={i === active ? "text-on-dark" : "text-on-dark-subtle"} />
      ))}
    </nav>
  );
}

/* Botão fechar (modal) */
export function CloseButton({ onClick }: { onClick?: () => void }) {
  return (
    <button onClick={onClick} aria-label="Fechar" className="grid size-7 place-items-center rounded-full bg-paper-100">
      <X size={14} />
    </button>
  );
}

/* Action tile */
export function ActionTile({ icon: Icon, label, onClick, disabled }: { icon: LucideIcon; label: string; onClick?: () => void; disabled?: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="flex h-16 flex-1 flex-col items-center justify-center gap-1.5 rounded-md border border-paper-border text-micro font-medium hover:bg-paper-100 disabled:cursor-not-allowed disabled:opacity-40"
    >
      <Icon size={16} /> {label}
    </button>
  );
}

/* Linha de detalhe */
export function DetailRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2.5 text-body-sm">
      <span className="text-text-secondary">{label}</span>
      <span className="text-right font-semibold">{children}</span>
    </div>
  );
}

export const shortHash = (a?: string | null) =>
  a && a.length > 12 ? `${a.slice(0, 6)}…${a.slice(-4)}` : a ?? "—";

/* Trunca endereços/hashes que aparecem dentro de textos livres (explicações, evidências, violações) */
export const shortenAddrs = (text: string) => text.replace(/0x[0-9a-fA-F]{16,}/g, (m) => shortHash(m));

/* Hash truncado em mono, com copiar */
export function Hash({ value, className }: { value?: string | null; className?: string }) {
  const [ok, setOk] = useState(false);
  if (!value) return <span className="font-mono text-text-tertiary">—</span>;
  async function copy() {
    try {
      await navigator.clipboard.writeText(value!);
      setOk(true);
      setTimeout(() => setOk(false), 1200);
    } catch {}
  }
  return (
    <button
      type="button"
      onClick={copy}
      title={ok ? "Copiado" : `Copiar ${value}`}
      className={clsx("inline-flex items-center gap-1.5 font-mono text-caption", className)}
    >
      {shortHash(value)}
      {ok ? <Check size={12} className="text-positive" /> : <Copy size={12} className="text-text-tertiary" />}
    </button>
  );
}

/* Hero com formas granuladas (onboarding) */
export function GrainHero({ className }: { className?: string }) {
  return (
    <div aria-hidden className={clsx("pointer-events-none overflow-hidden", className ?? "relative h-[420px]")}>
      <div className="grain-strong absolute left-[30%] top-[-10%] h-[45%] w-[30%] -rotate-[35deg]" />
      <div className="grain-strong absolute left-[5%] top-[25%] h-[50%] w-[75%] -rotate-[35deg] opacity-90" />
      <div className="absolute left-[55%] top-[35%] h-[18%] w-[2px] -rotate-[35deg] bg-white/70" />
      <div className="grain-strong absolute left-[35%] top-[55%] h-[40%] w-[50%] -rotate-[35deg] brightness-150" />
    </div>
  );
}
