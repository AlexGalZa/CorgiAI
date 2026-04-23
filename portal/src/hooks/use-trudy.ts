"use client";

import { useState, useEffect, useCallback } from "react";
import { UseFormSetValue, FieldValues } from "react-hook-form";
import {
  createSession,
  getSession,
  sendMessage,
  claimSession,
  AibMessage,
} from "@/lib/aib-api";
import { mapExtractedFields } from "@/lib/trudy-field-map";
import { useQuoteStore } from "@/stores/use-quote-store";

interface UseTrudyOptions<T extends FieldValues> {
  step: string;
  setValue: UseFormSetValue<T>;
  jwt?: string;
  isNewQuote?: boolean;
  quoteNumber?: string;
}

interface TrudyState {
  messages: AibMessage[];
  isLoading: boolean;
  greeting: string | null;
  sessionId: string | null;
  sessionToken: string | null;
  sendError: string | null;
}

export function useTrudy<T extends FieldValues>({
  step,
  setValue,
  jwt,
  isNewQuote = false,
  quoteNumber,
}: UseTrudyOptions<T>) {
  const { updateTrudyExtracted } = useQuoteStore();

  // Per-quote scoped keys so two different quotes (or users) on the same
  // browser never collide.
  const scope = quoteNumber ?? "new";
  const sessionIdKey = `trudy_session_id_${scope}`;
  const sessionTokenKey = `trudy_session_token_${scope}`;

  const [state, setState] = useState<TrudyState>({
    messages: [],
    isLoading: false,
    greeting: null,
    sessionId: null,
    sessionToken: null,
    sendError: null,
  });

  useEffect(() => {
    async function initSession() {
      const storedId = localStorage.getItem(sessionIdKey);
      const storedToken = localStorage.getItem(sessionTokenKey);

      if (storedId && storedToken) {
        try {
          const detail = await getSession(storedId, storedToken);
          setState((s) => ({
            ...s,
            sessionId: storedId,
            sessionToken: storedToken,
            messages: detail.messages,
            greeting:
              detail.messages.length === 0 && isNewQuote
                ? getGreeting(step)
                : null,
          }));
          return;
        } catch {
          // Session expired or invalid — fall through to create new
        }
      }

      const session = await createSession();
      localStorage.setItem(sessionIdKey, session.session_id);
      localStorage.setItem(sessionTokenKey, session.session_token);
      setState((s) => ({
        ...s,
        sessionId: session.session_id,
        sessionToken: session.session_token,
        messages: [],
        greeting: isNewQuote ? getGreeting(step) : null,
      }));
    }

    initSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionIdKey, sessionTokenKey]);

  useEffect(() => {
    if (!jwt || !state.sessionId || !state.sessionToken) return;
    claimSession(state.sessionId, state.sessionToken, jwt).catch(() => {
      // Non-critical
    });
  }, [jwt, state.sessionId, state.sessionToken]);

  const sendUserMessage = useCallback(
    async (content: string, file?: File) => {
      if (!state.sessionId || !state.sessionToken || (!content.trim() && !file)) return;

      const displayContent = file ? `[Attached: ${file.name}]\n\n${content}` : content;
      const userMsg: AibMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: displayContent,
        file_name: file?.name ?? null,
        extracted_fields: {},
        created_at: new Date().toISOString(),
      };

      setState((s) => ({
        ...s,
        messages: [...s.messages, userMsg],
        isLoading: true,
        greeting: null,
        sendError: null,
      }));

      try {
        const res = await sendMessage(
          state.sessionId,
          state.sessionToken,
          content,
          step,
          file
        );

        const assistantMsg: AibMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: res.message,
          file_name: null,
          extracted_fields: res.extracted_fields,
          created_at: new Date().toISOString(),
        };

        setState((s) => ({
          ...s,
          messages: [...s.messages, assistantMsg],
          isLoading: false,
        }));

        const mapped = mapExtractedFields(res.extracted_fields);
        for (const [field, value] of Object.entries(mapped)) {
          setValue(field as Parameters<UseFormSetValue<T>>[0], value as Parameters<UseFormSetValue<T>>[1], {
            shouldValidate: false,
            shouldDirty: true,
          });
        }
        // Also persist to store so other form sections can pick up the
        // extracted values via their defaultValues.
        if (Object.keys(mapped).length > 0) {
          updateTrudyExtracted(mapped);
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Something went wrong. Please try again.";
        setState((s) => ({ ...s, isLoading: false, sendError: msg }));
      }
    },
    [state.sessionId, state.sessionToken, step, setValue, updateTrudyExtracted]
  );

  return {
    messages: state.messages,
    isLoading: state.isLoading,
    greeting: state.greeting,
    sendError: state.sendError,
    sendMessage: sendUserMessage as (content: string, file?: File) => Promise<void>,
  };
}

function getGreeting(step: string): string {
  const greetings: Record<string, string> = {
    "get-started":
      "Hi! I'm your Corgi Advisor. Tell me about your business — what does your company do, and what kind of coverage are you looking for?",
    company:
      "Let's get your company details set. What's the legal name of your business, and roughly how many employees do you have?",
    "coverage-intro":
      "What's your business address? I'll need the full street address, city, state, and ZIP.",
    coverage:
      "Now for a few coverage-specific questions. I'll keep it brief — these help us get you the right quote.",
    "claims-history":
      "Have you had any insurance claims in the past few years, or do you currently carry any business insurance policies?",
    products:
      "Here's what's available based on what you've told me. Let me know if you'd like me to explain any of these coverages.",
    summary:
      "Here's a summary of everything. Take a look and let me know if anything needs correcting.",
  };
  return greetings[step] ?? "Hi! I'm your Corgi Advisor. How can I help?";
}
