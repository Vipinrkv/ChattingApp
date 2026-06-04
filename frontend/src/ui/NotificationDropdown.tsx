import React, { useState } from 'react';
import { useNotifications } from '../hooks/useNotifications';
import './notification.css';

export default function NotificationDropdown() {
  const { notifications, unreadCount, loading, refresh, markRead } = useNotifications();
  const [open, setOpen] = useState(false);

  return (
    <div className="notification-dropdown">
      <button className="notif-button" onClick={() => { setOpen((o) => !o); if (!open) void refresh(); }} aria-label="Notifications">
        <span className="bell">🔔</span>
        {unreadCount > 0 && <span className="badge">{unreadCount}</span>}
      </button>

      {open && (
        <div className="notif-panel">
          <div className="notif-header">Notifications</div>
          {loading && <div className="notif-empty">Loading…</div>}
          {!loading && notifications.length === 0 && <div className="notif-empty">No notifications</div>}
          <ul className="notif-list">
            {notifications.map((n) => (
              <li key={n.id} className={`notif-item ${n.is_read ? 'read' : 'unread'}`} onClick={() => void markRead(n.id)}>
                <div className="notif-text">{n.text ?? n.type}</div>
                <div className="notif-meta">{new Date(n.timestamp).toLocaleString()}</div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
