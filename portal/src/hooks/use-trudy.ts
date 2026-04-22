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

const SESSION_ID_KEY = "trudy_session_id";
const SESSION_TOKEN_KEY = "trudy_session_token";

interface UseTrudyOptions<T extends FieldValues> {
  step: string;
  setValue: UseFormSetValue<T>;
  jwt?: string;
  isNewQuote?: boolean;
}

interface TrudyState {
  messages: AibMessage[];
  isLoading: boolean;
  greeting: string | null;
  sessionId: string | null;
  sessionToken: string | null;
}

export function useTrudy<T extends FieldValues>({
  step,
  setValue,
  jwt,
  isNewQuote = false,
}: UseTrudyOptions<T>) {
  const [state, setState] = useState<TrudyState>({
    messages: [],
    isLoading: false,
    greeting: null,
    sessionId: null,
    sessionToken: null,
  });

  useEffect(() => {
    async function initSession() {
      const storedId = localStorage.getItem(SESSION_ID_KEY);
      const storedToken = localStorage.getItem(SESSION_TOKEN_KEY);

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
      localStorage.setItem(SESSION_ID_KEY, session.session_id);
      localStorage.setItem(SESSION_TOKEN_KEY, session.session_token);
      setState((s) => ({
        ...s,
        sessionId: session.session_id,
        sessionToken: session.session_token,
        messages: [],
        greeting: isNewQuote ? getGreeting(step) : null,
      }));
    }

    initSession();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!jwt || !state.sessionId || !state.sessionToken) return;
    claimSession(state.sessionId, state.sessionToken, jwt).catch(() => {
      // Non-critical
    });
  }, [jwt, state.sessionId, state.sessionToken]);

  const sendUserMessage = useCallback(
    async (content: string) => {
      if (!state.sessionId || !state.sessionToken || !content.trim()) return;

      const userMsg: AibMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content,
        extracted_fields: {},
        created_at: new Date().toISOString(),
      };

      setState((s) => ({
        ...s,
        messages: [...s.messages, userMsg],
        isLoading: true,
        greeting: null,
      }));

      try {
        const res = await sendMessage(
          state.sessionId,
          state.sessionToken,
          content,
          step
        );

        const assistantMsg: AibMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: res.message,
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
      } catch {
        setState((s) => ({ ...s, isLoading: false }));
      }
    },
    [state.sessionId, state.sessionToken, step, setValue]
  );

  return {
    messages: state.messages,
    isLoading: state.isLoading,
    greeting: state.greeting,
    sendMessage: sendUserMessage,
  };
}

function getGreeting(step: string): string {
  const greetings: Record<string, string> = {
    "get-started":
      "Hi! I'm Trudy, your Corgi insurance advisor. Tell me about your business — what does your company do, and what kind of coverage are you looking for?",
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
  return greetings[step] ?? "Hi! I'm Trudy. How can I help?";
}
