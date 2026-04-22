const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface AibSession {
  session_id: string;
  session_token: string;
}

export interface AibMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  extracted_fields: Record<string, unknown>;
  created_at: string;
}

export interface AibSessionDetail {
  session_id: string;
  messages: AibMessage[];
}

export interface SendMessageResponse {
  message: string;
  extracted_fields: Record<string, string | number | null>;
}

async function aibFetch<T>(
  path: string,
  options: RequestInit & { sessionToken?: string; jwt?: string } = {}
): Promise<T> {
  const { sessionToken, jwt, ...rest } = options;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(sessionToken ? { "X-AIB-Token": sessionToken } : {}),
    ...(jwt ? { Authorization: `Bearer ${jwt}` } : {}),
  };
  const res = await fetch(`${API_BASE}/api/v1/aib${path}`, { ...rest, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`AIB API error ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export async function createSession(): Promise<AibSession> {
  return aibFetch<AibSession>("/sessions/", { method: "POST" });
}

export async function getSession(
  sessionId: string,
  sessionToken: string
): Promise<AibSessionDetail> {
  return aibFetch<AibSessionDetail>(`/sessions/${sessionId}/`, { sessionToken });
}

export async function sendMessage(
  sessionId: string,
  sessionToken: string,
  content: string,
  step: string
): Promise<SendMessageResponse> {
  return aibFetch<SendMessageResponse>(`/sessions/${sessionId}/messages/`, {
    method: "POST",
    sessionToken,
    body: JSON.stringify({ content, step }),
  });
}

export async function claimSession(
  sessionId: string,
  sessionToken: string,
  jwt: string
): Promise<void> {
  await aibFetch(`/sessions/${sessionId}/claim/`, {
    method: "POST",
    jwt,
    body: JSON.stringify({ session_token: sessionToken }),
  });
}
