import { useState, useCallback, useEffect, useRef } from 'react';
import { sendMessage, sendMessageWithFile, completeSession, getSession, getIntake } from '../services/api';

const OPENING_MESSAGE = {
  role: 'assistant',
  content: "Hi! I'm your AI insurance advisor. Tell me about your business and I'll help get the right specialty coverage in front of your broker, fast.\n\nWhat type of coverage are you looking for?",
  attachments: [],
  timestamp: new Date().toISOString(),
  synthetic: true,
};

export function useChat(sessionId) {
  const [messages, setMessages] = useState([OPENING_MESSAGE]);
  const [isLoading, setIsLoading] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [intake, setIntake] = useState(null);
  const [error, setError] = useState(null);
  const lastUserContentRef = useRef('');

  useEffect(() => {
    if (sessionId) {
      loadExistingMessages(sessionId);
    }
  }, [sessionId]);

  async function loadExistingMessages(sid) {
    try {
      const session = await getSession(sid);
      if (session && session.messages && session.messages.length > 0) {
        setMessages(session.messages.map(m => ({
          role: m.role,
          content: m.content,
          attachments: m.attachments || [],
          timestamp: m.created_at,
        })));
        if (session.status === 'completed') {
          setIsComplete(true);
          try {
            const intakeData = await getIntake(sid);
            setIntake(intakeData);
          } catch {
            // Intake may not exist yet
          }
        }
      }
      // If no messages, the initial OPENING_MESSAGE state is already correct
    } catch {
      // Session may be new — opening message already in state
    }
  }

  const send = useCallback(async (content, file = null) => {
    if (!sessionId || isLoading) return;
    if (!content.trim() && !file) return;

    setError(null);
    lastUserContentRef.current = content;

    const userMsg = {
      role: 'user',
      content: content || '',
      timestamp: new Date().toISOString(),
      attachments: file ? [{
        filename: file.name,
        type: file.type.includes('pdf') ? 'pdf' : 'image',
        size: file.size,
      }] : [],
    };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);

    try {
      let response;
      if (file) {
        response = await sendMessageWithFile(sessionId, content, file);
      } else {
        response = await sendMessage(sessionId, content);
      }

      const assistantMsg = {
        role: 'assistant',
        content: response.content,
        attachments: [],
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, assistantMsg]);

      if (response.is_complete) {
        try {
          const result = await completeSession(sessionId);
          setIntake(result.intake);
          setIsComplete(true);
        } catch (err) {
          console.error('Failed to complete session:', err);
        }
      }
    } catch (err) {
      setError(err.message);
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, isLoading]);

  return { messages, isLoading, isComplete, intake, error, send, lastUserContent: lastUserContentRef.current };
}
