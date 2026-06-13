// frontend/src/lib/websocket.ts
export const WS_EVENT = {
  MESSAGE: 'message',
  TYPING: 'typing',
  MESSAGE_READ: 'message_read',
  PING: 'ping',
  PONG: 'pong',
  CONNECTED: 'connected',
  DISCONNECTED: 'disconnected',
  ERROR: 'error',
} as const;

export type WebSocketEventType = typeof WS_EVENT[keyof typeof WS_EVENT];
export type SocketStatus = 'idle' | 'connecting' | 'connected' | 'reconnecting' | 'disconnected' | 'error';

export interface WebSocketMessage {
  type: WebSocketEventType;
  data?: unknown;
  error?: string;
}

type MessageHandler = (payload: WebSocketMessage) => void;
type StatusHandler = (status: SocketStatus) => void;

const managerRegistry = new Map<string, WebSocketManager>();

function resolveSocketApiBase(): string {
  const envApiBase = import.meta.env.VITE_API_BASE;
  const envApiUrl = import.meta.env.VITE_API_URL;

  // Prioritize VITE_API_URL if it points to a remote server (e.g. Render backend)
  if (envApiUrl && !envApiUrl.includes('localhost') && !envApiUrl.includes('127.0.0.1') && !envApiUrl.includes('::1')) {
    return envApiUrl;
  }

  if (envApiBase) {
    // If VITE_API_BASE is a remote server, use it
    if (!envApiBase.includes('localhost') && !envApiBase.includes('127.0.0.1') && !envApiBase.includes('::1')) {
      return envApiBase;
    }

    // If it's a localhost URL, check if the app itself is running on localhost
    if (typeof window !== 'undefined') {
      const currentHost = window.location.hostname;
      const isPageLocalhost = ['localhost', '127.0.0.1', '::1'].includes(currentHost);
      if (isPageLocalhost) {
        return envApiBase;
      }
    }
  }

  // Fallback to VITE_API_URL if VITE_API_BASE was a localhost proxy that we bypassed
  if (envApiUrl) {
    return envApiUrl;
  }

  const currentHost = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
  return typeof window !== 'undefined'
    ? `${window.location.protocol}//${currentHost}:8000`
    : 'http://localhost:8000';
}

function getSocketKey(peerId: string, channelType: 'chat' | 'group') {
  return `${channelType}:${peerId}`;
}

export class WebSocketManager {
  private ws: WebSocket | null = null;
  private url: string;
  private token: string | null = null;
  private peerId: string;
  private channelType: 'chat' | 'group';
  private eventHandlers: Map<string, Set<MessageHandler>> = new Map();
  private statusHandlers: Set<StatusHandler> = new Set();
  private status: SocketStatus = 'idle';
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 7;
  private minReconnectDelay = 1000;
  private maxReconnectDelay = 30000;
  private isIntentionallyClosed = false;
  private isConnecting = false;
  private sendQueue: Array<Record<string, unknown>> = [];
  private reconnectTimer: number | null = null;
  private heartbeatTimer: number | null = null;
  private heartbeatInterval = 25000;
  private lastPong: number | null = null;

  private constructor(peerId: string, channelType: 'chat' | 'group' = 'chat') {
    const apiBase = resolveSocketApiBase();
    const wsBase = import.meta.env.VITE_WS_BASE;

    window.addEventListener('auth:token-refresh', ((event: CustomEvent<string>) => {
      this.refreshToken(event.detail);
    }) as EventListener);

    if (wsBase) {
      let resolvedUrl = wsBase.replace(/\/$/, '');
      try {
        // Normalize ws/wss protocols to http/https for URL parsing
        const wsUrlObj = new URL(resolvedUrl.replace(/^ws:/, 'http:').replace(/^wss:/, 'https:'));
        const apiUrlObj = new URL(apiBase);
        if (wsUrlObj.hostname !== apiUrlObj.hostname) {
          console.warn(`[WebSocket] Hostname mismatch! wsBase: ${wsUrlObj.hostname}, apiBase: ${apiUrlObj.hostname}. Rewriting WebSocket hostname.`);
          wsUrlObj.hostname = apiUrlObj.hostname;
          wsUrlObj.port = apiUrlObj.port;
          resolvedUrl = wsUrlObj.toString().replace(/^http:/, 'ws:').replace(/^https:/, 'wss:').replace(/\/$/, '');
        }
      } catch (e) {
        console.error('[WebSocket] Failed to parse wsBase, falling back to apiBase', e);
      }
      this.url = resolvedUrl;
    } else {
      const url = new URL(apiBase);
      url.pathname = '';
      url.search = '';
      url.hash = '';
      this.url = url.toString().replace(/^http:/, 'ws:').replace(/^https:/, 'wss:').replace(/\/$/, '');
    }

    this.peerId = peerId;
    this.channelType = channelType;
  }

  static getInstance(peerId: string, channelType: 'chat' | 'group' = 'chat'): WebSocketManager {
    const key = getSocketKey(peerId, channelType);
    if (!managerRegistry.has(key)) {
      managerRegistry.set(key, new WebSocketManager(peerId, channelType));
    }

    return managerRegistry.get(key)!;
  }

  static disposeInstance(peerId: string, channelType: 'chat' | 'group' = 'chat'): void {
    const key = getSocketKey(peerId, channelType);
    const manager = managerRegistry.get(key);
    if (manager) {
      manager.disconnect();
      managerRegistry.delete(key);
    }
  }

  getPeerId() {
    return this.peerId;
  }

  getChannelType() {
    return this.channelType;
  }

  getStatus() {
    return this.status;
  }

  async connect(token: string, forceReconnect = false): Promise<void> {
    if (!token) {
      throw new Error('WebSocket auth token is required');
    }

    const shouldReconnect = forceReconnect || (this.ws?.readyState === WebSocket.OPEN && this.token !== token);
    const isOpen = this.ws?.readyState === WebSocket.OPEN;

    if (isOpen && !shouldReconnect) {
      return;
    }

    if (this.isConnecting) {
      if (this.token !== token) {
        this.token = token;
      }
      return;
    }

    this.token = token;
    this.isIntentionallyClosed = false;
    this.setStatus(isOpen ? 'reconnecting' : 'connecting');

    if (isOpen) {
      this.closeConnection();
    }

    return new Promise((resolve, reject) => {
      let settled = false;
      try {
        this.isConnecting = true;
        let hasOpened = false;
        let handshakeFailed = false;
        const route = this.channelType === 'group' ? 'groups' : 'chat';
        const wsUrl = `${this.url}/ws/${route}/${this.peerId}?token=${encodeURIComponent(token)}`;
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          hasOpened = true;
          this.reconnectAttempts = 0;
          this.flushQueue();
          this.startHeartbeat();
          this.isConnecting = false;
          this.setStatus('connected');
          if (!settled) {
            settled = true;
            resolve();
          }
        };

        this.ws.onmessage = (event) => {
          try {
            const payload = JSON.parse(event.data) as WebSocketMessage;
            if (payload.type === WS_EVENT.PONG) {
              this.handlePong();
            }
            this.emitEvent(payload);
          } catch (err) {
            console.error('Failed to parse WebSocket message:', err);
            this.emitEvent({ type: WS_EVENT.ERROR, error: 'Invalid payload' });
          }
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          this.setStatus('error');
          if (this.isConnecting && !hasOpened) {
            handshakeFailed = true;
            if (!settled) {
              settled = true;
              reject(error instanceof Error ? error : new Error('WebSocket error'));
            }
          }
        };

        this.ws.onclose = (event) => {
          this.stopHeartbeat();
          this.isConnecting = false;
          if (this.isIntentionallyClosed) {
            this.setStatus('disconnected');
            return;
          }

          const policyRejected = event.code === 1008 || event.code === 1002 || event.code === 1003;
          if (handshakeFailed || policyRejected) {
            this.setStatus('error');
            if (!settled) {
              settled = true;
              reject(new Error('WebSocket connection rejected'));
            }
            return;
          }

          if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.attemptReconnect();
            return;
          }

          this.setStatus('disconnected');
        };
      } catch (err) {
        this.isConnecting = false;
        this.setStatus('error');
        if (!settled) {
          settled = true;
          reject(err instanceof Error ? err : new Error('WebSocket connection failed'));
        }
      }
    });
  }

  refreshToken(token: string): void {
    if (!token || token === this.token) {
      return;
    }

    this.token = token;
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.setStatus('reconnecting');
      this.closeConnection();
    }

    if (!this.isIntentionallyClosed) {
      void this.connect(token).catch((err) => {
        console.error('WebSocket token refresh failed:', err);
      });
    }
  }

  send(payload: Record<string, unknown>): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload));
      return;
    }

    if (this.sendQueue.length >= 100) {
      this.sendQueue.shift();
    }

    this.sendQueue.push(payload);
    if (!this.isIntentionallyClosed && this.reconnectAttempts < this.maxReconnectAttempts) {
      this.attemptReconnect();
    }
  }

  sendTyping(): void {
    this.send({ type: WS_EVENT.TYPING });
  }

  sendReadReceipt(messageId: string): void {
    this.send({ type: WS_EVENT.MESSAGE_READ, message_id: messageId });
  }

  sendPing(): void {
    this.send({ type: WS_EVENT.PING });
  }

  private flushQueue(): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return;
    }

    while (this.sendQueue.length > 0) {
      const payload = this.sendQueue.shift();
      if (payload) {
        this.ws.send(JSON.stringify(payload));
      }
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectTimer || this.isConnecting) {
      return;
    }
    this.reconnectAttempts += 1;
    const delay = this.getReconnectDelay();
    this.setStatus('reconnecting');

    if (this.reconnectTimer) {
      window.clearTimeout(this.reconnectTimer);
    }

    this.reconnectTimer = window.setTimeout(() => {
      if (this.token && !this.isIntentionallyClosed) {
        void this.connect(this.token, true).catch((err) => {
          console.error('Reconnection failed:', err);
        });
      }
    }, delay);
  }

  private getReconnectDelay(): number {
    return Math.min(this.minReconnectDelay * 2 ** (this.reconnectAttempts - 1), this.maxReconnectDelay);
  }

  private setStatus(status: SocketStatus): void {
    if (this.status === status) {
      return;
    }

    this.status = status;
    this.statusHandlers.forEach((handler) => handler(status));
  }

  private emitEvent(payload: WebSocketMessage): void {
    const handlers = this.eventHandlers.get(payload.type);
    if (handlers) {
      handlers.forEach((handler) => handler(payload));
    }

    const anyHandlers = this.eventHandlers.get('any');
    if (anyHandlers) {
      anyHandlers.forEach((handler) => handler(payload));
    }
  }

  on(eventType: WebSocketEventType | 'any', handler: MessageHandler): () => void {
    const handlers = this.eventHandlers.get(eventType) ?? new Set<MessageHandler>();
    handlers.add(handler);
    this.eventHandlers.set(eventType, handlers);
    return () => {
      handlers.delete(handler);
      if (handlers.size === 0) {
        this.eventHandlers.delete(eventType);
      }
    };
  }

  onMessage(handler: MessageHandler): () => void {
    return this.on('any', handler);
  }

  onStatusChange(handler: StatusHandler): () => void {
    this.statusHandlers.add(handler);
    handler(this.status);
    return () => {
      this.statusHandlers.delete(handler);
    };
  }

  isConnected(): boolean {
    return this.status === 'connected';
  }

  disconnect(): void {
    this.isIntentionallyClosed = true;
    this.stopHeartbeat();

    if (this.reconnectTimer) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    this.closeConnection();
    this.setStatus('disconnected');
  }

  release(): void {
    if (this.eventHandlers.size === 0 && this.statusHandlers.size === 0) {
      const key = getSocketKey(this.peerId, this.channelType);
      managerRegistry.delete(key);
      this.disconnect();
    }
  }

  private closeConnection(): void {
    if (this.ws) {
      try {
        this.ws.close();
      } catch {
        // ignore close errors
      }
    }
    this.ws = null;
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = window.setTimeout(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.sendPing();
      }
      this.startHeartbeat();
    }, this.heartbeatInterval);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      window.clearTimeout(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private handlePong(): void {
    this.lastPong = Date.now();
  }
}
