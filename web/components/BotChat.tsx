"use client";
import { useEffect, useRef, useState } from "react";

export type ChatMsg = { role: "user" | "bot" | "system"; text: string };
export type Suggestion = { label: string; text: string };

export default function BotChat({
  messages,
  onSend,
  busy,
  suggestions = [],
}: {
  messages: ChatMsg[];
  onSend: (t: string) => void;
  busy: boolean;
  suggestions?: Suggestion[];
}) {
  const [text, setText] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  function send() {
    if (!text.trim() || busy) return;
    onSend(text.trim());
    setText("");
  }

  return (
    <div className="card grid">
      <div className="chat">
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            {m.text}
          </div>
        ))}
        <div ref={endRef} />
      </div>

      {suggestions.length > 0 && (
        <div className="chips">
          {suggestions.map((s) => (
            <button key={s.label} type="button" className="btn btn-ghost" onClick={() => setText(s.text)} disabled={busy}>
              {s.label}
            </button>
          ))}
        </div>
      )}

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            send();
          }
        }}
        placeholder="Ex.: pague 10 USDT ao fornecedor"
        style={{ minHeight: 96 }}
      />
      <div>
        <button className={`btn ${busy ? "loading" : ""}`} onClick={send} disabled={busy || !text.trim()}>
          {busy ? "Agente trabalhando…" : "Enviar ao agente"}
        </button>
      </div>
    </div>
  );
}