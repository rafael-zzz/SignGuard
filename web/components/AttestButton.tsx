"use client";
import { useState } from "react";
import { ArrowUpRight, Stamp } from "lucide-react";
import { attest } from "@/lib/api";
import { OutlineButton } from "./ui";

export default function AttestButton({ analysisId }: { analysisId: string }) {
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onClick() {
    setBusy(true);
    try {
      const r = await attest(analysisId);
      setMsg(
        r.mocked
          ? "Atestado simulado (configure o contrato no backend)."
          : r.explorer_url ?? "Atestado enviado, mas sem link do explorer."
      );
    } catch (e) {
      setMsg(`Erro: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid justify-items-start gap-2 sm:justify-items-end">
      <OutlineButton icon={Stamp} onClick={onClick} disabled={busy}>
        {busy ? "Registrando…" : "Registrar atestado on-chain"}
      </OutlineButton>
      {msg &&
        (msg.startsWith("http") ? (
          <p className="text-caption text-text-tertiary">
            <a href={msg} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-0.5 font-semibold text-text-primary underline-offset-2 hover:underline">
              Ver no explorer <ArrowUpRight size={12} />
            </a>{" "}
            · confirmando na blockchain (~15 s)
          </p>
        ) : (
          <p className="text-caption text-text-tertiary">{msg}</p>
        ))}
    </div>
  );
}
