import React from 'react';

export default function TypingIndicator() {
  return (
    <div className="message-row message-row-assistant">
      <div className="message-avatar">🐕</div>
      <div className="message-bubble message-bubble-assistant typing-indicator">
        <div className="typing-dots">
          <span className="typing-dot"></span>
          <span className="typing-dot"></span>
          <span className="typing-dot"></span>
        </div>
      </div>
    </div>
  );
}
