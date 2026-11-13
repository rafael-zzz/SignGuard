"use client";
import { useEffect, useRef, useState } from "react";
import clsx from "clsx";
import { Chip, PrimaryButton } from "./ui";

export type ChatTone = "ok" | "warn" | "block";
export type ChatMsg = { role: "user" | "bot" | "system"; text: string; tone?: ChatTone };
export type Suggestion = { label: string; text: string };

const toneDot: Record<ChatTone, string> = { ok: "bg-positive", warn: "bg-warning", block: "bg-negative" };

export function ChatBubble({ role, text, tone }: ChatMsg) {
  if (role === "system")
    return (
      <div className="mx-auto inline-flex max-w-full items-center gap-2 px-2 py-1 text-center text-caption text-text-tertiary [overflow-wrap:anywhere]">
        {tone && <span className={clsx("size-1.5 shrink-0 rounded-full", toneDot[tone])} />}
        {text}
      </div>
    );
  return (
    <div
      className={clsx(
        "max-w-[85%] animate-rise rounded-lg px-3.5 py-2.5 text-body-sm [overflow-wrap:anywhere]",
        role === "user" ? "ml-auto rounded-br-sm bg-ink-950 text-on-dark" : "mr-auto rounded-bl-sm bg-paper-100 text-text-primary",
      )}
    >
      {text}
    </div>
  );
}

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
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // rola só a caixa do chat, sem arrastar a página inteira
    const el = listRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages]);

  function send() {
    if (!text.trim() || busy) return;
    onSend(text.trim());
    setText("");
  }

  return (
    <div className="grid min-w-0 grid-cols-1 gap-3">
      <div
        ref={listRef}
        className="flex max-h-[400px] min-h-64 flex-col gap-2 overflow-y-auto rounded-lg border border-paper-border p-3"
      >
        {messages.map((m, i) => (
          <ChatBubble key={i} {...m} />
        ))}
      </div>

      {suggestions.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {suggestions.map((s) => (
            <Chip key={s.label} active={text === s.text} onClick={() => !busy && setText(s.text)}>
              {s.label}
            </Chip>
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
        aria-label="Mensagem para o agente"
        placeholder="Ex.: pague 10 USDT ao fornecedor"
        className="min-h-24 w-full resize-y rounded-md border border-paper-border bg-paper-100 px-4 py-3 text-body-sm text-text-primary placeholder:text-text-tertiary focus:border-text-primary focus:outline-none"
      />
      <PrimaryButton onClick={send} disabled={!text.trim()} loading={busy}>
        {busy ? "Agente trabalhando…" : "Enviar ao agente"}
      </PrimaryButton>
    </div>
  );
}
