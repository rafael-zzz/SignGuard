"use client";
// Tela Analisar (04-design-brief). Dono: Caio.
import { useEffect, useState } from "react";
import VerdictCard from "@/components/VerdictCard";
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
      <header className="hero">
        <span className="eyebrow">Proteção antes da assinatura</span>
        <h1>Entenda antes de <span className="grad">assinar</span>.</h1>
        <p className="muted">Cole a transação ou escolha um exemplo. Os agentes explicam o que ela faz e se você deve assinar.</p>
      </header>

      <div className="card grid">
        <div className="chips">
          {scenarios.map((s) => (
            <button key={s.id} className={`btn ${selected === s.id ? "" : "btn-ghost"}`} onClick={() => pick(s)}>
              {s.label}
            </button>
          ))}
        </div>
        <textarea
          value={raw}
          onChange={(e) => setRaw(e.target.value)}
          placeholder='{"from":"0x...","to":"0x...","data":"0x...","value":"0","chain_id":1,"owner_id":"default"}'
        />
        <div>
          <button className={`btn ${loading ? "loading" : ""}`} onClick={run} disabled={!raw || loading}>
            {loading ? "Analisando…" : "Analisar antes de assinar"}
          </button>
        </div>
        {error && <p style={{ color: "var(--block)" }}>{error}</p>}
      </div>

      {result && <VerdictCard v={result} />}
    </main>
  );
}
