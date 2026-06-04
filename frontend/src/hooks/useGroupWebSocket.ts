//frontend/src/hooks/useGroupWebSocket.ts
import { useCallback, useEffect, useRef, useState } from 'react';
import { WebSocketManager } from '../lib/websocket';
import { useAuth } from '../contexts/AuthContext';

interface WebSocketMessage {
  type: string;
  data?: unknown;
  error?: string;
}

export function useGroupWebSocket(groupId: string | null) {
  const { token } = useAuth();
  const managerRef = useRef<WebSocketManager | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);

  useEffect(() => {
    setMessages([]);
    setError(null);
    setIsConnected(false);
    setIsConnecting(false);

    if (!token || !groupId) {
      return;
    }

    const manager = WebSocketManager.getInstance(groupId, 'group');
    managerRef.current = manager;

    const unsubscribeStatus = manager.onStatusChange((status) => {
      setIsConnected(status === 'connected');
      setIsConnecting(status === 'connecting' || status === 'reconnecting');
      if (status === 'error') {
        setError('Group WebSocket connection error');
      }
    });

    const unsubscribeMessage = manager.onMessage((payload) => {
      setMessages((prev) => [...prev.slice(-199), payload as WebSocketMessage]);
    });

    setIsConnecting(true);

    manager.connect(token).catch((err) => {
      setError(err instanceof Error ? err.message : 'Connection failed');
    });

    return () => {
      unsubscribeMessage();
      unsubscribeStatus();
      manager.release();
      managerRef.current = null;
      setIsConnecting(false);
      setIsConnected(false);
    };
  }, [token, groupId]);

  const sendMessage = useCallback((content: string) => {
    if (!managerRef.current) {
      setError('WebSocket is not initialized');
      return;
    }
    managerRef.current.send({ type: 'message', content });
  }, []);

  return {
    isConnected,
    isConnecting,
    error,
    messages,
    sendMessage,
  };
}
