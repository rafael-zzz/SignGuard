"use client";
import { PrimaryButton } from "./ui";

export default function TxForm({
  value, onChange, onSubmit, loading, error,
}: { value: string; onChange: (v: string) => void; onSubmit: () => void; loading: boolean; error?: string | null }) {
  return (
    <div className="grid grid-cols-1 gap-3">
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        spellCheck={false}
        aria-label="Transação em JSON"
        placeholder='{"from":"0x...","to":"0x...","data":"0x...","value":"0","chain_id":1,"owner_id":"default"}'
        className="min-h-44 w-full resize-y rounded-md border border-paper-border bg-paper-100 px-4 py-3 font-mono text-caption leading-relaxed text-text-primary placeholder:text-text-tertiary focus:border-text-primary focus:outline-none"
      />
      {error && <p className="text-body-sm font-medium text-negative">{error}</p>}
      <PrimaryButton onClick={onSubmit} disabled={!value} loading={loading}>
        {loading ? "Os agentes estão analisando…" : "Analisar antes de assinar"}
      </PrimaryButton>
    </div>
  );
}
