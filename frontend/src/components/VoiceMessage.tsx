import React, { useRef, useState } from 'react';

interface VoiceMessageProps {
  receiverId: string;
  onSendVoiceMessage?: (audioUrl: string) => void;
}

export function VoiceMessage({ receiverId, onSendVoiceMessage }: VoiceMessageProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [duration, setDuration] = useState(0);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const timerRef = useRef<number | null>(null);
  const timeoutRef = useRef<number | null>(null);

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      recorderRef.current = mediaRecorder;
      const chunks: Blob[] = [];

      mediaRecorder.onstart = () => {
        setIsRecording(true);
        setDuration(0);
        if (timerRef.current) {
          window.clearInterval(timerRef.current);
        }
        timerRef.current = window.setInterval(() => {
          setDuration((prev) => prev + 1);
        }, 1000);
      };

      mediaRecorder.ondataavailable = (e) => chunks.push(e.data);
      mediaRecorder.onstop = async () => {
        setIsRecording(false);
        if (timerRef.current) {
          window.clearInterval(timerRef.current);
          timerRef.current = null;
        }
        if (timeoutRef.current) {
          window.clearTimeout(timeoutRef.current);
          timeoutRef.current = null;
        }

        const blob = new Blob(chunks, { type: 'audio/webm' });
        const initialization = new FormData();
        initialization.append('filename', 'voice.webm');

        const initRes = await fetch('/api/v1/media/upload/initiate', { method: 'POST', body: initialization });
        const { upload_id } = await initRes.json();

        const chunkForm = new FormData();
        chunkForm.append('chunk_index', '0');
        chunkForm.append('file', blob);
        await fetch(`/api/v1/media/upload/${upload_id}/chunk`, { method: 'POST', body: chunkForm });

        const completeForm = new FormData();
        completeForm.append('filename', 'voice.webm');
        const completeRes = await fetch(`/api/v1/media/upload/${upload_id}/complete`, { method: 'POST', body: completeForm });
        const { url } = await completeRes.json();

        setAudioUrl(url);
        onSendVoiceMessage?.(url);

        if (mediaRecorder.stream) {
          mediaRecorder.stream.getTracks().forEach((track) => track.stop());
        }
      };

      mediaRecorder.start();
      timeoutRef.current = window.setTimeout(() => {
        if (recorderRef.current && recorderRef.current.state === 'recording') {
          recorderRef.current.stop();
        }
      }, 60000);
    } catch (err) {
      console.error('Recording error:', err);
    }
  }

  function stopRecording() {
    if (recorderRef.current && recorderRef.current.state === 'recording') {
      recorderRef.current.stop();
    }
    if (timeoutRef.current) {
      window.clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    setIsRecording(false);
  }

  return (
    <div className="voice-message">
      <button
        onClick={isRecording ? stopRecording : startRecording}
        className={`voice-btn ${isRecording ? 'recording' : ''}`}
        title="Record voice message"
      >
        🎤 {isRecording ? `${duration}s` : 'Voice'}
      </button>
      {audioUrl && (
        <div className="voice-preview">
          <audio src={audioUrl} controls className="voice-player" />
        </div>
      )}
    </div>
  );
}
