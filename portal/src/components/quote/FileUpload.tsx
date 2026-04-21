'use client';

import { useState, useCallback, useRef, type DragEvent } from 'react';

interface Props {
  label?: string;
  accept?: string;
  maxFiles?: number;
  files: File[];
  onChange: (files: File[]) => void;
}

export function FileUpload({ label, accept, maxFiles = 5, files, onChange }: Props) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback((e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const dropped = Array.from(e.dataTransfer.files);
    const combined = [...files, ...dropped].slice(0, maxFiles);
    onChange(combined);
  }, [files, maxFiles, onChange]);

  const handleSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files || []);
    const combined = [...files, ...selected].slice(0, maxFiles);
    onChange(combined);
  }, [files, maxFiles, onChange]);

  const removeFile = (index: number) => {
    onChange(files.filter((_, i) => i !== index));
  };

  return (
    <div>
      {label && (
        <label className="text-[11px] font-semibold text-heading mb-1 block tracking-normal leading-[1.2]">{label}</label>
      )}
      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-6 text-center transition-colors cursor-pointer ${isDragging ? 'border-primary bg-primary/5' : 'border-border hover:border-primary'}`}
      >
        <input ref={inputRef} type="file" accept={accept} multiple className="hidden" onChange={handleSelect} />
        <p className="text-sm text-muted">
          Drag & drop files here, or <span className="text-primary font-medium">browse</span>
        </p>
        {maxFiles > 1 && (
          <p className="text-[11px] text-muted mt-1">Up to {maxFiles} files</p>
        )}
      </div>

      {files.length > 0 && (
        <div className="mt-2 space-y-1">
          {files.map((f, i) => (
            <div key={i} className="flex items-center justify-between bg-bg rounded-lg px-3 py-2">
              <span className="text-xs text-body truncate">{f.name}</span>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); removeFile(i); }}
                className="text-muted hover:text-heading text-xs bg-transparent border-none cursor-pointer"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
