"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import { FieldValues, UseFormSetValue } from "react-hook-form";
import { useTrudy } from "@/hooks/use-trudy";
import { MessageBubble } from "./MessageBubble";

const ACCEPTED_TYPES = ["application/pdf", "image/jpeg", "image/png", "image/gif", "image/webp"];
const MAX_BYTES = 10 * 1024 * 1024;

interface TrudyPanelProps<T extends FieldValues> {
  step: string;
  setValue: UseFormSetValue<T>;
  isNewQuote?: boolean;
  jwt?: string;
  quoteNumber?: string;
}

export function TrudyPanel<T extends FieldValues>({
  step,
  setValue,
  isNewQuote = false,
  jwt,
  quoteNumber,
}: TrudyPanelProps<T>) {
  const [input, setInput] = useState("");
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragCounterRef = useRef(0);

  const { messages, isLoading, greeting, sendError, sendMessage } = useTrudy({
    step,
    setValue,
    isNewQuote,
    jwt,
    quoteNumber,
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading, greeting]);

  const validateAndAttach = useCallback((file: File) => {
    setFileError(null);
    if (!ACCEPTED_TYPES.includes(file.type)) {
      setFileError("Only PDF, JPEG, PNG, GIF, or WebP files are supported.");
      return;
    }
    if (file.size > MAX_BYTES) {
      setFileError("File must be under 10 MB.");
      return;
    }
    setAttachedFile(file);
  }, []);

  const handleSend = () => {
    const trimmed = input.trim();
    if ((!trimmed && !attachedFile) || isLoading) return;
    setInput("");
    setAttachedFile(null);
    setFileError(null);
    sendMessage(trimmed, attachedFile ?? undefined);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) validateAndAttach(file);
    e.target.value = "";
  };

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    dragCounterRef.current += 1;
    if (dragCounterRef.current === 1) setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    dragCounterRef.current -= 1;
    if (dragCounterRef.current === 0) setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    dragCounterRef.current = 0;
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) validateAndAttach(file);
  };

  return (
    <div
      className="flex flex-col h-full bg-bg border-l border-border min-h-0 relative"
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {/* Drag overlay */}
      {isDragging && (
        <div className="absolute inset-0 z-10 bg-primary/10 border-2 border-dashed border-primary rounded-lg flex items-center justify-center pointer-events-none">
          <p className="text-primary font-semibold text-sm">Drop file to attach</p>
        </div>
      )}

      <div className="flex items-center gap-2 px-4 py-3 border-b border-border flex-shrink-0">
        <div className="w-7 h-7 rounded-full bg-primary flex items-center justify-center">
          <span className="text-white text-xs font-bold">T</span>
        </div>
        <div>
          <p className="text-sm font-semibold text-foreground">Corgi Advisor</p>
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

        {sendError && (
          <div className="flex justify-center">
            <p className="text-[11px] text-error bg-error/10 px-3 py-1.5 rounded-lg">{sendError}</p>
          </div>
        )}

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
        {/* File chip */}
        {attachedFile && (
          <div className="flex items-center gap-1.5 mb-2 px-2 py-1 bg-surface border border-border rounded-lg w-fit max-w-full">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-muted flex-shrink-0">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
            <span className="text-xs text-foreground truncate max-w-[180px]">{attachedFile.name}</span>
            <button
              onClick={() => { setAttachedFile(null); setFileError(null); }}
              className="text-muted hover:text-foreground ml-0.5 flex-shrink-0"
              aria-label="Remove attachment"
            >
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        )}

        {fileError && (
          <p className="text-[10px] text-error mb-1.5">{fileError}</p>
        )}

        <div className="flex gap-2 items-end">
          {/* Attach button */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isLoading}
            className="h-9 w-9 rounded-xl border border-border bg-surface text-muted flex items-center justify-center flex-shrink-0 hover:text-foreground hover:border-primary/50 transition-colors disabled:opacity-40"
            aria-label="Attach file"
            title="Attach PDF or image"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
            </svg>
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,image/jpeg,image/png,image/gif,image/webp"
            className="hidden"
            onChange={handleFileInputChange}
          />

          <textarea
            className="flex-1 resize-none rounded-xl border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary/50 min-h-[40px] max-h-[120px]"
            placeholder="Ask Corgi Advisor anything..."
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={(!input.trim() && !attachedFile) || isLoading}
            className="h-9 w-9 rounded-xl bg-primary text-white flex items-center justify-center flex-shrink-0 disabled:opacity-40 hover:bg-primary/90 transition-colors"
            aria-label="Send"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M22 2L11 13M22 2L15 22l-4-9-9-4 20-7z" />
            </svg>
          </button>
        </div>
        <p className="text-[10px] text-muted mt-1.5 text-center">
          Corgi Advisor fills in the form as you chat · drag & drop or attach PDF/images
        </p>
      </div>
    </div>
  );
}
