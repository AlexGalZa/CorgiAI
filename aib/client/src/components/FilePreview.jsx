import React from 'react';

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

export default function FilePreview({ file, onRemove }) {
  if (!file) return null;

  const isPdf = file.type === 'application/pdf';
  const isImage = file.type.startsWith('image/');
  const previewUrl = isImage ? URL.createObjectURL(file) : null;

  return (
    <div className="file-preview-strip">
      <div className="file-preview-item">
        {isImage && previewUrl ? (
          <img
            src={previewUrl}
            alt={file.name}
            className="file-preview-thumbnail"
            onLoad={() => URL.revokeObjectURL(previewUrl)}
          />
        ) : (
          <div className="file-preview-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
          </div>
        )}
        <div className="file-preview-info">
          <span className="file-preview-name">{file.name}</span>
          <span className="file-preview-size">
            {isPdf ? 'PDF • ' : ''}{formatFileSize(file.size)}
          </span>
        </div>
        <button
          className="file-preview-remove"
          onClick={onRemove}
          title="Remove file"
          type="button"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>
    </div>
  );
}
