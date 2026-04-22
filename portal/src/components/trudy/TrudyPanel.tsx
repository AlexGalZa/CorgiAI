"use client";

import { useRef, useEffect, useState } from "react";
import { FieldValues, UseFormSetValue } from "react-hook-form";
import { useTrudy } from "@/hooks/use-trudy";
import { MessageBubble } from "./MessageBubble";

interface TrudyPanelProps<T extends FieldValues> {
  step: string;
  setValue: UseFormSetValue<T>;
  isNewQuote?: boolean;
  jwt?: string;
}

export function TrudyPanel<T extends FieldValues>({
  step,
  setValue,
  isNewQuote = false,
  jwt,
}: TrudyPanelProps<T>) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const { messages, isLoading, greeting, sendMessage } = useTrudy({
    step,
    setValue,
    isNewQuote,
    jwt,
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading, greeting]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;
    setInput("");
    sendMessage(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full bg-bg border-l border-border min-h-0">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border flex-shrink-0">
        <div className="w-7 h-7 rounded-full bg-primary flex items-center justify-center">
          <span className="text-white text-xs font-bold">T</span>
        </div>
        <div>
          <p className="text-sm font-semibold text-foreground">Trudy</p>
          <p className="text-[10px] text-muted">AI Insurance Advisor</p>
        </div>
        <div className="ml-auto w-2 h-2 rounded-full bg-success" title="Online" />
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0">
        {greeting && messages.length === 0 && (
          <div className="flex gap-2">
            <div className="w-6 h-6 rounded-full bg-primary flex items-center justify-center flex-shrink-0 mt-1">
              <span className="text-white text-[10px] font-bold">T</span>
            </div>
            <div className="max-w-[85%] rounded-2xl rounded-tl-sm px-3 py-2 text-sm bg-surface border border-border text-foreground">
              {greeting}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isLoading && (
          <div className="flex gap-2">
            <div className="w-6 h-6 rounded-full bg-primary flex items-center justify-center flex-shrink-0 mt-1">
              <span className="text-white text-[10px] font-bold">T</span>
            </div>
            <div className="bg-surface border border-border rounded-2xl rounded-tl-sm px-3 py-2.5">
              <div className="flex gap-1 items-center">
                <span className="w-1.5 h-1.5 bg-muted rounded-full animate-bounce [animation-delay:0ms]" />
                <span className="w-1.5 h-1.5 bg-muted rounded-full animate-bounce [animation-delay:150ms]" />
                <span className="w-1.5 h-1.5 bg-muted rounded-full animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div className="border-t border-border p-3 flex-shrink-0">
        <div className="flex gap-2 items-end">
          <textarea
            className="flex-1 resize-none rounded-xl border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary/50 min-h-[40px] max-h-[120px]"
            placeholder="Ask Trudy anything..."
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="h-9 w-9 rounded-xl bg-primary text-white flex items-center justify-center flex-shrink-0 disabled:opacity-40 hover:bg-primary/90 transition-colors"
            aria-label="Send"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M22 2L11 13M22 2L15 22l-4-9-9-4 20-7z" />
            </svg>
          </button>
        </div>
        <p className="text-[10px] text-muted mt-1.5 text-center">
          Trudy fills in the form as you chat
        </p>
      </div>
    </div>
  );
}
