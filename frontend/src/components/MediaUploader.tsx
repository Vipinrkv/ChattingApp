import React, { useState } from 'react';
import { apiPost } from '../lib/api';

const CHUNK_SIZE = 1024 * 1024 * 4; // 4MB

export function MediaUploader({ onComplete }: { onComplete?: (url: string) => void }) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [preview, setPreview] = useState<string | null>(null);

  const uploadFile = async (file: File) => {
    setUploading(true);
    try {
      const form = new FormData();
      form.append('filename', file.name);
      const initRes = await fetch('/api/v1/media/upload/initiate', { method: 'POST', body: form });
      const initJson = await initRes.json();
      const uploadId = initJson.upload_id;

      const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
      for (let i = 0; i < totalChunks; i++) {
        const start = i * CHUNK_SIZE;
        const chunk = file.slice(start, start + CHUNK_SIZE);
        const chunkForm = new FormData();
        chunkForm.append('chunk_index', String(i));
        chunkForm.append('file', chunk, file.name);
        await fetch(`/api/v1/media/upload/${uploadId}/chunk`, { method: 'POST', body: chunkForm });
        setProgress(Math.round(((i + 1) / totalChunks) * 100));
      }

      const completeForm = new FormData();
      completeForm.append('filename', file.name);
      const completeRes = await fetch(`/api/v1/media/upload/${uploadId}/complete`, { method: 'POST', body: completeForm });
      const completeJson = await completeRes.json();
      const url = completeJson.url;
      setPreview(url || null);
      if (onComplete && url) onComplete(url);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="media-uploader">
      <label className="ghost-button">
        {uploading ? `Uploading ${progress}%` : 'Upload Media'}
        <input
          type="file"
          accept="image/*,video/*"
          className="hidden-input"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) uploadFile(f);
          }}
        />
      </label>
      {preview ? (
        <div className="media-preview">
          {preview.endsWith('.mp4') || preview.endsWith('.webm') ? (
            <video src={preview} width={320} controls />
          ) : (
            <img src={preview} alt="preview" width={320} />
          )}
        </div>
      ) : null}
    </div>
  );
}

export default MediaUploader;
