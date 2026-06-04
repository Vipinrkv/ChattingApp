import React, { useState } from 'react';
import { apiPost, apiDelete, apiGet } from '../lib/api';

interface MessageBookmarkProps {
  messageId: string;
  onBookmarkChange?: (isBookmarked: boolean) => void;
}

export function MessageBookmark({ messageId, onBookmarkChange }: MessageBookmarkProps) {
  const [isBookmarked, setIsBookmarked] = useState(false);
  const [label, setLabel] = useState('');
  const [showLabelInput, setShowLabelInput] = useState(false);

  async function toggleBookmark() {
    try {
      if (isBookmarked) {
        await apiDelete(`/api/v1/chats/bookmarks/${messageId}`);
      } else {
        await apiPost(`/api/v1/chats/bookmarks/${messageId}${label ? `?label=${encodeURIComponent(label)}` : ''}`, {});
      }
      setIsBookmarked(!isBookmarked);
      setLabel('');
      setShowLabelInput(false);
      onBookmarkChange?.(!isBookmarked);
    } catch (err) {
      console.error('Bookmark error:', err);
    }
  }

  return (
    <div className="message-bookmark">
      <button
        className={`bookmark-btn ${isBookmarked ? 'active' : ''}`}
        onClick={() => setShowLabelInput(!showLabelInput)}
        title={isBookmarked ? 'Remove bookmark' : 'Add bookmark'}
      >
        🔖
      </button>
      {showLabelInput && (
        <div className="bookmark-input-group">
          <input
            type="text"
            placeholder="Label (optional)"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            className="bookmark-label-input"
          />
          <button onClick={toggleBookmark} className="confirm-btn">
            {isBookmarked ? 'Remove' : 'Save'}
          </button>
        </div>
      )}
    </div>
  );
}

export async function fetchUserBookmarks(limit: number = 100, offset: number = 0) {
  try {
    const response = await apiGet(`/api/v1/chats/bookmarks?limit=${limit}&offset=${offset}`);
    return response;
  } catch (err) {
    console.error('Failed to fetch bookmarks:', err);
    return null;
  }
}
