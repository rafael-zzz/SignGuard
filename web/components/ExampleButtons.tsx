import type { Scenario } from "@/lib/types";

export default function ExampleButtons({
  scenarios, selected, onPick,
}: { scenarios: Scenario[]; selected: string | null; onPick: (s: Scenario) => void }) {
  return (
    <div className="chips">
      {scenarios.map((s) => (
        <button key={s.id} className={`btn ${selected === s.id ? "" : "btn-ghost"}`} onClick={() => onPick(s)}>
          {s.label}
        </button>
      ))}
    </div>
  );
}