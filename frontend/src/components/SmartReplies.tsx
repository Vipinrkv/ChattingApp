import React, { useState, useEffect } from 'react';
import { apiGet } from '../lib/api';

interface SmartRepliesProps {
  messageId: string;
  onReplySelected?: (text: string) => void;
}

export function SmartReplies({ messageId, onReplySelected }: SmartRepliesProps) {
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSuggestions();
  }, [messageId]);

  async function loadSuggestions() {
    try {
      const response = await apiGet(`/api/v1/chats/messages/${messageId}/smart-replies`);
      setSuggestions(response.suggestions || []);
    } catch (err) {
      console.error('Failed to load smart replies:', err);
    } finally {
      setLoading(false);
    }
  }

  if (loading || !suggestions.length) return null;

  return (
    <div className="smart-replies">
      <label className="smart-replies-label">✨ Smart Replies:</label>
      <div className="smart-replies-container">
        {suggestions.map((suggestion) => (
          <button
            key={suggestion.reply_id}
            onClick={() => onReplySelected?.(suggestion.text)}
            className="smart-reply-btn"
            title={`${(suggestion.confidence * 100).toFixed(0)}% match`}
          >
            {suggestion.text}
          </button>
        ))}
      </div>
    </div>
  );
}
