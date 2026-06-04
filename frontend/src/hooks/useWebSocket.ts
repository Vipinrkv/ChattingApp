// frontend/src/hooks/useWebSocket.ts
import { useEffect, useRef, useState, useCallback } from 'react';
import { WebSocketManager } from '../lib/websocket';
import { useAuth } from '../contexts/AuthContext';

interface WebSocketMessage {
  type: string;
  data?: unknown;
  error?: string;
}

export function useWebSocket(peerId: string | null) {
  const { token } = useAuth();
  const managerRef = useRef<WebSocketManager | null>(null);
  const typingTimeoutRef = useRef<number | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);

  useEffect(() => {
    setMessages([]);
    setError(null);
    setIsConnected(false);
    setIsConnecting(false);

    if (!token || !peerId) {
      return;
    }

    const manager = WebSocketManager.getInstance(peerId, 'chat');
    managerRef.current = manager;

    const unsubscribeStatus = manager.onStatusChange((status) => {
      setIsConnected(status === 'connected');
      setIsConnecting(status === 'connecting' || status === 'reconnecting');
      if (status === 'error') {
        setError('WebSocket connection error');
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
      if (typingTimeoutRef.current) {
        window.clearTimeout(typingTimeoutRef.current);
        typingTimeoutRef.current = null;
      }
    };
  }, [token, peerId]);

  const sendMessage = useCallback((content: string) => {
    if (!managerRef.current) {
      setError('WebSocket is not initialized');
      return;
    }

    managerRef.current.send({ type: 'message', content });
  }, []);

  const sendTyping = useCallback(() => {
    if (!managerRef.current?.isConnected()) {
      return;
    }

    if (typingTimeoutRef.current) {
      return;
    }

    managerRef.current.sendTyping();
    typingTimeoutRef.current = window.setTimeout(() => {
      typingTimeoutRef.current = null;
    }, 2000);
  }, []);

  const sendReadReceipt = useCallback((messageId: string) => {
    if (!managerRef.current?.isConnected()) {
      return;
    }

    managerRef.current.sendReadReceipt(messageId);
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return {
    isConnected,
    isConnecting,
    error,
    messages,
    sendMessage,
    sendTyping,
    sendReadReceipt,
    clearMessages,
  };
}
