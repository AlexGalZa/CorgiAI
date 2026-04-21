import { useState, useEffect } from 'react';
import { createSession, getSession } from '../services/api';

const SESSION_KEY = 'aib_session_id';

export function useSession() {
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    initSession();
  }, []);

  async function initSession() {
    setLoading(true);
    setError(null);

    try {
      // Check localStorage for existing session
      const stored = localStorage.getItem(SESSION_KEY);
      if (stored) {
        // Verify session still exists and is active
        try {
          const session = await getSession(stored);
          if (session && session.status === 'active') {
            setSessionId(stored);
            setLoading(false);
            return;
          }
        } catch {
          // Session not found or invalid, create new one
          localStorage.removeItem(SESSION_KEY);
        }
      }

      // Create new session
      const session = await createSession();
      localStorage.setItem(SESSION_KEY, session.id);
      setSessionId(session.id);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function resetSession() {
    localStorage.removeItem(SESSION_KEY);
    initSession();
  }

  return { sessionId, loading, error, resetSession };
}
