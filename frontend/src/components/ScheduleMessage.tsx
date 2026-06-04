import React, { useState } from 'react';
import { apiPost, apiDelete } from '../lib/api';

interface ScheduleMessageProps {
  receiverId: string;
  onScheduled?: () => void;
}

export function ScheduleMessage({ receiverId, onScheduled }: ScheduleMessageProps) {
  const [showScheduler, setShowScheduler] = useState(false);
  const [content, setContent] = useState('');
  const [scheduledFor, setScheduledFor] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSchedule() {
    if (!content.trim() || !scheduledFor) return;

    try {
      setLoading(true);
      await apiPost(`/api/v1/chats/${receiverId}/messages/schedule`, {
        content,
        scheduled_for: new Date(scheduledFor).toISOString(),
      });
      setContent('');
      setScheduledFor('');
      setShowScheduler(false);
      onScheduled?.();
    } catch (err) {
      console.error('Schedule error:', err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="schedule-message">
      <button onClick={() => setShowScheduler(!showScheduler)} className="schedule-btn" title="Schedule message">
        ⏰
      </button>
      {showScheduler && (
        <div className="schedule-form">
          <textarea
            placeholder="Message content"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="schedule-textarea"
          />
          <input
            type="datetime-local"
            value={scheduledFor}
            onChange={(e) => setScheduledFor(e.target.value)}
            className="schedule-datetime"
            aria-label="Scheduled date and time"
          />
          <button onClick={handleSchedule} disabled={loading || !content.trim() || !scheduledFor} className="schedule-send">
            {loading ? 'Scheduling...' : 'Schedule'}
          </button>
        </div>
      )}
    </div>
  );
}
