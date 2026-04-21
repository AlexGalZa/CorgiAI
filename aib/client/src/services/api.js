const API_BASE = '/api';

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  const response = await fetch(url, config);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Request failed' }));
    throw new Error(error.error || `HTTP ${response.status}`);
  }

  return response.json();
}

// Sessions
export async function createSession() {
  return request('/sessions', { method: 'POST' });
}

export async function getSession(sessionId) {
  return request(`/sessions/${sessionId}`);
}

// Chat — text only
export async function sendMessage(sessionId, content, attachments = []) {
  return request('/chat/message', {
    method: 'POST',
    body: JSON.stringify({
      session_id: sessionId,
      content,
      attachments,
    }),
  });
}

// Chat — with file attachment (multipart/form-data)
export async function sendMessageWithFile(sessionId, content, file) {
  const url = `${API_BASE}/chat/message`;
  const formData = new FormData();
  formData.append('session_id', sessionId);
  formData.append('content', content || '');
  formData.append('file', file);

  // Don't set Content-Type header — browser will set it with boundary
  const response = await fetch(url, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Request failed' }));
    throw new Error(error.error || `HTTP ${response.status}`);
  }

  return response.json();
}

export async function completeSession(sessionId) {
  return request(`/chat/${sessionId}/complete`, { method: 'POST' });
}

// Intakes
export async function getIntake(sessionId) {
  return request(`/intakes/${sessionId}`);
}
