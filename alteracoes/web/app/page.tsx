"use client";
// Tela Analisar (04-design-brief + design-system.md). Dono: Caio.
import { useEffect, useState } from "react";
import ExampleButtons from "@/components/ExampleButtons";
import TxForm from "@/components/TxForm";
import VerdictCard from "@/components/VerdictCard";
import { GrainHero, Overline, Sheet } from "@/components/ui";
import { analyzeScenario, analyzeTx, getScenarios } from "@/lib/api";
import type { Scenario, TxInput, Verdict } from "@/lib/types";

export default function Page() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [raw, setRaw] = useState("");
  const [result, setResult] = useState<Verdict | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getScenarios().then(setScenarios).catch((e) => setError(String(e)));
  }, []);

  function pick(s: Scenario) {
    setSelected(s.id);
    setRaw(JSON.stringify(s.tx, null, 2));
    setResult(null);
  }

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const fromScenario = selected && scenarios.find((s) => s.id === selected && JSON.stringify(s.tx, null, 2) === raw);
      setResult(fromScenario ? await analyzeScenario(selected!) : await analyzeTx(JSON.parse(raw) as TxInput));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <header className="relative pb-10 pt-6 sm:pb-14 sm:pt-10">
        <GrainHero className="absolute -right-12 top-0 hidden h-full w-[50%] opacity-70 lg:block" />
        <div className="relative max-w-md">
          <p className="mb-3 text-overline font-semibold uppercase text-on-dark-muted">Proteção antes da assinatura</p>
          <h1 className="font-serif text-display sm:text-[52px] sm:leading-[56px]">Entenda antes de assinar.</h1>
          <p className="mt-4 text-body text-on-dark-muted">
            Cole a transação ou escolha um exemplo. Os agentes explicam o que ela faz e se você deve assinar.
          </p>
        </div>
      </header>

      <Sheet title="Nova análise" action={<span />} className="-mx-4 min-h-[60vh] sm:mx-0">
        <Overline>Exemplos</Overline>
        <ExampleButtons scenarios={scenarios} selected={selected} onPick={pick} />
        <Overline className="mt-6">Transação</Overline>
        <TxForm value={raw} onChange={setRaw} onSubmit={run} loading={loading} error={error} />
        {result && <VerdictCard v={result} />}
      </Sheet>
    </main>
  );
}
