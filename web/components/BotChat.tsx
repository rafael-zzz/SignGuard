"use client";
import { useState } from "react";
import clsx from "clsx";
import { PrimaryButton } from "./ui";

export type ChatMsg = { role: "user" | "bot" | "system"; text: string };

export function ChatBubble({ role, text }: ChatMsg) {
  return (
    <div
      className={clsx(
        "max-w-[85%] break-words rounded-lg px-3.5 py-2.5 text-body-sm [overflow-wrap:anywhere]",
        role === "user" && "ml-auto rounded-br-sm bg-ink-950 text-on-dark",
        role === "bot" && "rounded-bl-sm bg-paper-100 text-text-primary",
        role === "system" && "mx-auto bg-transparent text-center text-caption text-text-tertiary",
      )}
    >
      {text}
    </div>
  );
}

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
    <div className="grid grid-cols-1 gap-3">
      <div className="grid grid-cols-1 gap-2">
        {messages.map((m, i) => <ChatBubble key={i} {...m} />)}
      </div>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Ex.: pague 10 USDT ao fornecedor"
        className="min-h-24 w-full resize-y rounded-md border border-paper-border bg-paper-100 px-4 py-3 text-body-sm text-text-primary placeholder:text-text-tertiary focus:border-text-primary focus:outline-none"
      />
      <PrimaryButton onClick={send} disabled={!text.trim()} loading={busy}>
        {busy ? "Agente trabalhando…" : "Enviar ao agente"}
      </PrimaryButton>
    </div>
  );
}
