"use client";
import { useState } from "react";

export const short = (a?: string | null) =>
  a && a.length > 12 ? `${a.slice(0, 6)}…${a.slice(-4)}` : a ?? "—";

export default function AddressChip({ address }: { address?: string | null }) {
  const [ok, setOk] = useState(false);
  async function copy() {
    if (!address) return;
    try {
      await navigator.clipboard.writeText(address);
      setOk(true);
      setTimeout(() => setOk(false), 1200);
    } catch {}
  }
  return (
    <span className="hash-row">
      <span className="addr" title={address ?? ""}>{short(address)}</span>
      {address && (
        <button type="button" className="copy-btn" onClick={copy}>
          {ok ? "copiado ✓" : "copiar"}
        </button>
      )}
    </span>
  );
}