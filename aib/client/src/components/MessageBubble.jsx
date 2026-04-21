import React from 'react';
import ReactMarkdown from 'react-markdown';

function formatFileSize(bytes) {
  if (!bytes) return '';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user';
  const attachments = message.attachments || [];

  // Strip [INTAKE_COMPLETE] marker from display
  const displayContent = message.content.replace('[INTAKE_COMPLETE]', '').trim();

  return (
    <div className={`message-row ${isUser ? 'message-row-user' : 'message-row-assistant'}`}>
      {!isUser && (
        <div className="message-avatar">🐕</div>
      )}
      <div className={`message-bubble ${isUser ? 'message-bubble-user' : 'message-bubble-assistant'}`}>
        {/* Attachment indicators */}
        {attachments.length > 0 && (
          <div className="message-attachments">
            {attachments.map((att, i) => (
              <div key={i} className={`message-attachment ${isUser ? 'message-attachment-user' : ''}`}>
                {att.type === 'pdf' ? (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                    <line x1="16" y1="13" x2="8" y2="13" />
                    <line x1="16" y1="17" x2="8" y2="17" />
                  </svg>
                ) : (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                    <circle cx="8.5" cy="8.5" r="1.5" />
                    <polyline points="21 15 16 10 5 21" />
                  </svg>
                )}
                <span className="message-attachment-name">{att.filename}</span>
                {att.size && (
                  <span className="message-attachment-size">{formatFileSize(att.size)}</span>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Message text */}
        {displayContent && (
          isUser ? (
            <p className="message-text">{displayContent}</p>
          ) : (
            <div className="message-markdown">
              <ReactMarkdown>{displayContent}</ReactMarkdown>
            </div>
          )
        )}
      </div>
    </div>
  );
}
