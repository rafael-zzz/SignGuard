"use client";
// Header escuro: marca + navegação em pills (design-system.md §6 "Pill secundário")
import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import { Bot, ScanSearch, ShieldCheck } from "lucide-react";

const LINKS = [
  { href: "/", label: "Analisar", icon: ScanSearch },
  { href: "/agente", label: "Agente-carteira", icon: Bot },
];

export default function AppNav() {
  const path = usePathname();
  return (
    <nav className="flex items-center justify-between py-5">
      <Link href="/" className="flex items-center gap-2 text-body font-semibold tracking-tight text-on-dark">
        <span className="grid size-7 place-items-center rounded-full border border-ink-border bg-ink-850">
          <ShieldCheck size={14} />
        </span>
        SignGuard
      </Link>
      <div className="flex items-center gap-2">
        {LINKS.map(({ href, label, icon: Icon }) => {
          const active = path === href;
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              className={clsx(
                "inline-flex h-8 items-center gap-1.5 rounded-full border px-3 text-caption font-medium transition",
                active
                  ? "border-on-dark bg-on-dark text-ink-950"
                  : "border-ink-border bg-ink-850 text-on-dark hover:bg-ink-900",
              )}
            >
              <Icon size={14} /> <span className="hidden sm:inline">{label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
