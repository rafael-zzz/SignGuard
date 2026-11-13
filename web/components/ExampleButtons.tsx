"use client";
import type { Scenario } from "@/lib/types";
import { Chip } from "./ui";

export default function ExampleButtons({
  scenarios, selected, onPick,
}: { scenarios: Scenario[]; selected: string | null; onPick: (s: Scenario) => void }) {
  return (
    <div className="flex flex-wrap gap-2">
      {scenarios.map((s) => (
        <Chip key={s.id} active={selected === s.id} onClick={() => onPick(s)}>
          {s.label}
        </Chip>
      ))}
    </div>
  );
}
