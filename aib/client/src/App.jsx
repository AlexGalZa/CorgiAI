import React, { useRef, useEffect } from 'react';
import { useSession } from './hooks/useSession';
import { useChat } from './hooks/useChat';
import ChatHeader from './components/ChatHeader';
import MessageBubble from './components/MessageBubble';
import TypingIndicator from './components/TypingIndicator';
import InputBar from './components/InputBar';
import CompletionPanel from './components/CompletionPanel';
import { quickStartChips } from './constants/theme';

export default function App() {
  const { sessionId, loading: sessionLoading, error: sessionError, resetSession } = useSession();
  const { messages, isLoading, isComplete, intake, error: chatError, send } = useChat(sessionId);
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  function handleNewChat() {
    resetSession();
  }

  if (sessionLoading) {
    return (
      <div className="app-loading">
        <div className="app-loading-spinner"></div>
        <p>Setting up your session...</p>
      </div>
    );
  }

  if (sessionError) {
    return (
      <div className="app-error">
        <div className="app-error-icon">⚠️</div>
        <h2>Connection Error</h2>
        <p>{sessionError}</p>
        <button onClick={() => window.location.reload()}>Retry</button>
      </div>
    );
  }

  return (
    <div className="app">
      <ChatHeader onNewChat={handleNewChat} />

      <main className="chat-main">
        <div className="messages-container">
          {messages.length === 0 && !isLoading && (
            <div className="welcome-section">
              <div className="welcome-logo">
                <img src="/corgi-logo.webp" alt="Corgi Insurance" style={{ width: 72, height: 72, objectFit: 'contain' }} />
              </div>
              <h2 className="welcome-title">Welcome to Corgi Insurance</h2>
              <p className="welcome-text">
                Hi! I'm Trudy, your AI insurance advisor at Corgi Insurance. I'll help you get started with your
                specialty insurance needs — including analyzing your existing policies and recommending additional coverages. What can I help you with today?
              </p>
              <div className="quick-start-chips">
                {quickStartChips.map((chip, i) => (
                  <button
                    key={i}
                    className="quick-start-chip"
                    onClick={() => send(chip)}
                  >
                    {chip}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <MessageBubble key={i} message={msg} />
          ))}

          {isLoading && <TypingIndicator />}

          {chatError && (
            <div className="chat-error">
              <p>⚠️ {chatError}</p>
              <button onClick={() => send(messages[messages.length - 1]?.content || '')}>
                Retry
              </button>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {isComplete && intake && (
          <CompletionPanel intake={intake} onNewChat={handleNewChat} />
        )}
      </main>

      <InputBar onSend={send} disabled={isLoading || isComplete} />
    </div>
  );
}
