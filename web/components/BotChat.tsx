"use client";
import { useState } from "react";

export type ChatMsg = { role: "user" | "bot" | "system"; text: string };

export default function BotChat({
  messages, onSend, busy,
}: { messages: ChatMsg[]; onSend: (t: string) => void; busy: boolean }) {
  const [text, setText] = useState("");
  function send() {
    if (!text.trim() || busy) return;
    onSend(text.trim());
    setText("");
  }
  return (
    <div className="card grid">
      <div className="chat">
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>{m.text}</div>
        ))}
      </div>
      <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="Ex.: pague 10 USDT ao fornecedor" />
      <div>
        <button className="btn" onClick={send} disabled={busy || !text.trim()}>
          {busy ? "Agente trabalhando…" : "Enviar ao agente"}
        </button>
      </div>
    </div>
  );
}