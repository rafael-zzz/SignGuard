"use client";
import { useState } from "react";
import { attest } from "@/lib/api";

export default function AttestButton({ analysisId }: { analysisId: string }) {
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onClick() {
    setBusy(true);
    try {
      const r = await attest(analysisId);
      setMsg(r.mocked ? "Atestado simulado (configure o contrato no backend)." : r.explorer_url);
    } catch (e) {
      setMsg(`Erro: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <button className="btn" onClick={onClick} disabled={busy}>
        {busy ? "Registrando…" : "Registrar atestado on-chain"}
      </button>
      {msg &&
        (msg.startsWith("http") ? (
          <p><a href={msg} target="_blank" rel="noopener noreferrer" className="explorer-link">Ver no explorer ↗</a></p>
        ) : (
          <p className="muted">{msg}</p>
        ))}
    </div>
  );
}