export default function TxForm({
  value, onChange, onSubmit, loading, error,
}: { value: string; onChange: (v: string) => void; onSubmit: () => void; loading: boolean; error?: string | null }) {
  return (
    <>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder='{"from":"0x...","to":"0x...","data":"0x...","value":"0","chain_id":1,"owner_id":"default"}'
      />
      <div>
        <button className={`btn ${loading ? "loading" : ""}`} onClick={onSubmit} disabled={!value || loading}>
          {loading ? "Analisando…" : "Analisar antes de assinar"}
        </button>
      </div>
      {error && <p style={{ color: "var(--block)" }}>{error}</p>}
    </>
  );
}