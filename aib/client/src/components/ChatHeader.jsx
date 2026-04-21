import React from 'react';

export default function ChatHeader({ onNewChat }) {
  return (
    <header className="chat-header">
      <div className="chat-header-left">
        <div className="chat-header-logo">
          <img src="/corgi-logo.webp" alt="Corgi Insurance" style={{ width: 36, height: 36, objectFit: 'contain' }} />
        </div>
        <div className="chat-header-info">
          <h1 className="chat-header-title">Corgi Insurance Broker</h1>
          <p className="chat-header-subtitle">AI-Powered Insurance Intake</p>
        </div>
      </div>
      <button className="chat-header-new" onClick={onNewChat} title="Start new conversation">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 5v14M5 12h14" />
        </svg>
        New Chat
      </button>
    </header>
  );
}
