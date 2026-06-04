import { useEffect, useState, useCallback } from 'react';
import { apiGet, apiPatch } from '../lib/api';
import { WebSocketManager } from '../lib/websocket';
import { useAuth } from '../contexts/AuthContext';

export type Notification = {
  id: string;
  user_id: string;
  actor_id?: string | null;
  type: string;
  text?: string | null;
  data: Record<string, unknown>;
  is_read: boolean;
  timestamp: string;
};

let notificationsPromise: Promise<Notification[]> | null = null;
let currentUserPromise: Promise<{ id?: string }> | null = null;

async function loadNotifications() {
  if (!notificationsPromise) {
    notificationsPromise = apiGet('/api/v1/notifications')
      .then((payload) => (payload ?? []) as Notification[])
      .finally(() => {
        notificationsPromise = null;
      });
  }

  return notificationsPromise;
}

function loadCurrentUser() {
  if (!currentUserPromise) {
    currentUserPromise = apiGet('/api/v1/users/me')
      .then((payload) => payload as { id?: string })
      .finally(() => {
        currentUserPromise = null;
      });
  }

  return currentUserPromise;
}

export function useNotifications() {
  const { token, user, loading: authLoading } = useAuth();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);

  const fetchNotifications = useCallback(async () => {
    if (authLoading || !token || !user) {
      setNotifications([]);
      setUnreadCount(0);
      return;
    }

    setLoading(true);
    try {
      const payload = await loadNotifications();
      setNotifications(payload);
      const unread = payload.filter((n) => !n.is_read).length;
      setUnreadCount(unread);
    } catch (err) {
      // ignore for now
    } finally {
      setLoading(false);
    }
  }, [authLoading, token, user]);

  useEffect(() => {
    if (authLoading || !token || !user) return;
    void fetchNotifications();
  }, [authLoading, token, user, fetchNotifications]);

  useEffect(() => {
    if (!token || !user) return;
    let isCancelled = false;
    let unsubscribe: (() => void) | null = null;
    let manager: WebSocketManager | null = null;

    const connectNotifications = async () => {
      try {
        const currentUser = await loadCurrentUser();
        if (isCancelled || !currentUser.id) {
          return;
        }

        manager = WebSocketManager.getInstance(currentUser.id, 'chat');
        unsubscribe = manager.onMessage((payload) => {
          try {
            if ((payload as any).type === 'notification') {
              const notif = (payload as any).data as Notification;
              setNotifications((prev) => [notif, ...prev]);
              setUnreadCount((c) => c + (notif.is_read ? 0 : 1));
            }
          } catch {
            // noop
          }
        });

        await manager.connect(token);
      } catch {
        // Notification delivery still falls back to polling via fetchNotifications.
      }
    };

    void connectNotifications();

    return () => {
      isCancelled = true;
      unsubscribe?.();
      manager?.release();
    };
  }, [token, user]);

  const markRead = useCallback(async (id: string) => {
    try {
      await apiPatch(`/api/v1/notifications/${id}/read`);
      setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch (err) {
      // ignore for now
    }
  }, []);

  return {
    notifications,
    unreadCount,
    loading,
    refresh: fetchNotifications,
    markRead,
  };
}
