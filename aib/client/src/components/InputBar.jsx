import React, { useState, useRef, useEffect } from 'react';
import FilePreview from './FilePreview';

const ACCEPTED_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'application/pdf'];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB

export default function InputBar({ onSend, disabled, pendingFile, onPendingFileConsumed }) {
  const [input, setInput] = useState('');
  const [file, setFile] = useState(null);
  const [fileError, setFileError] = useState('');
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  function validateAndSetFile(f) {
    setFileError('');

    if (!ACCEPTED_TYPES.includes(f.type)) {
      setFileError('Only JPG, JPEG, PNG, and PDF files are accepted.');
      return;
    }
    if (f.size > MAX_FILE_SIZE) {
      setFileError('File is too large. Maximum size is 10 MB.');
      return;
    }

    setFile(f);
  }

  useEffect(() => {
    if (pendingFile) {
      validateAndSetFile(pendingFile);
      onPendingFileConsumed?.();
    }
  }, [pendingFile]);

  function handleSubmit(e) {
    e.preventDefault();
    if ((!input.trim() && !file) || disabled) return;
    onSend(input.trim(), file);
    setInput('');
    setFile(null);
    setFileError('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  }

  function handleInput(e) {
    setInput(e.target.value);
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 150) + 'px';
  }

  // ── File picker ──────────────────────────────────────────────────
  function handleAttachClick() {
    fileInputRef.current?.click();
  }

  function handleFileChange(e) {
    const f = e.target.files?.[0];
    if (f) validateAndSetFile(f);
    // Reset so the same file can be re-selected
    e.target.value = '';
  }

  function handleRemoveFile() {
    setFile(null);
    setFileError('');
  }

  const canSend = (input.trim() || file) && !disabled;

  return (
    <div className="input-bar-wrapper">
      {fileError && (
        <div className="file-error">
          <span>⚠️ {fileError}</span>
          <button type="button" onClick={() => setFileError('')}>✕</button>
        </div>
      )}

      <FilePreview file={file} onRemove={handleRemoveFile} />

      <form className="input-bar" onSubmit={handleSubmit}>
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".jpg,.jpeg,.png,.pdf"
          onChange={handleFileChange}
          style={{ display: 'none' }}
        />

        {/* Attach button */}
        <button
          type="button"
          className="input-attach-btn"
          onClick={handleAttachClick}
          disabled={disabled}
          title="Attach a file (JPG, PNG, PDF)"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
          </svg>
        </button>

        <textarea
          ref={textareaRef}
          className="input-textarea"
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder={disabled ? "Conversation complete" : file ? "Add a message about this file..." : "Type your message or drop a file..."}
          disabled={disabled}
          rows={1}
        />

        <button
          type="submit"
          className="input-send-btn"
          disabled={!canSend}
          title="Send message"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
          </svg>
        </button>
      </form>
    </div>
  );
}
