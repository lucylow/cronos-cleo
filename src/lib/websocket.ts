/**
 * WebSocket manager for real-time backend updates
 * Features:
 * - Automatic reconnection with exponential backoff
 * - Connection state management
 * - Event-based message handling
 * - Type-safe message handling
 */

// Simple EventEmitter implementation for browser
class EventEmitter {
  private events: Map<string, Function[]> = new Map();

  on(event: string, listener: Function): void {
    if (!this.events.has(event)) {
      this.events.set(event, []);
    }
    this.events.get(event)!.push(listener);
  }

  off(event: string, listener: Function): void {
    const listeners = this.events.get(event);
    if (listeners) {
      const index = listeners.indexOf(listener);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }

  emit(event: string, ...args: any[]): void {
    const listeners = this.events.get(event);
    if (listeners) {
      listeners.forEach(listener => {
        try {
          listener(...args);
        } catch (error) {
          console.error('Error in event listener:', error);
        }
      });
    }
  }

  once(event: string, listener: Function): void {
    const onceWrapper = (...args: any[]) => {
      this.off(event, onceWrapper);
      listener(...args);
    };
    this.on(event, onceWrapper);
  }

  removeAllListeners(event?: string): void {
    if (event) {
      this.events.delete(event);
    } else {
      this.events.clear();
    }
  }
}

const getApiBaseUrl = (): string => {
  if (typeof window !== 'undefined' && (window as any).__API_BASE_URL__) {
    return (window as any).__API_BASE_URL__;
  }
  try {
    return (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';
  } catch {
    return 'http://localhost:8000';
  }
};

export interface WebSocketMessage {
  type: string;
  data?: any;
  timestamp?: number;
}

export interface WebSocketOptions {
  path?: string;
  reconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  reconnectExponentialBackoff?: boolean;
  heartbeatInterval?: number;
}

export enum WebSocketState {
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  DISCONNECTING = 'disconnecting',
  DISCONNECTED = 'disconnected',
  ERROR = 'error',
}

class WebSocketManager extends EventEmitter {
  private ws: WebSocket | null = null;
  private url: string;
  private options: Required<WebSocketOptions>;
  private state: WebSocketState = WebSocketState.DISCONNECTED;
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private heartbeatTimeout: ReturnType<typeof setTimeout> | null = null;
  private messageQueue: WebSocketMessage[] = [];

  constructor(url: string, options: WebSocketOptions = {}) {
    super();
    this.url = url;
    this.options = {
      path: options.path || '',
      reconnect: options.reconnect !== false,
      reconnectInterval: options.reconnectInterval || 5000,
      maxReconnectAttempts: options.maxReconnectAttempts || 10,
      reconnectExponentialBackoff: options.reconnectExponentialBackoff !== false,
      heartbeatInterval: options.heartbeatInterval || 30000,
    };
  }

  connect(): void {
    if (this.state === WebSocketState.CONNECTING || this.state === WebSocketState.CONNECTED) {
      return;
    }

    this.setState(WebSocketState.CONNECTING);

    try {
      const wsUrl = this.url.replace(/^http/, 'ws') + this.options.path;
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.setState(WebSocketState.CONNECTED);
        this.reconnectAttempts = 0;
        this.startHeartbeat();
        
        // Send queued messages
        while (this.messageQueue.length > 0) {
          const message = this.messageQueue.shift();
          if (message) {
            this.send(message);
          }
        }

        this.emit('open');
      };

      this.ws.onmessage = (event) => {
        this.handleMessage(event);
      };

      this.ws.onerror = (error) => {
        this.setState(WebSocketState.ERROR);
        this.emit('error', error);
      };

      this.ws.onclose = () => {
        this.setState(WebSocketState.DISCONNECTED);
        this.stopHeartbeat();
        this.emit('close');

        if (this.options.reconnect && this.reconnectAttempts < this.options.maxReconnectAttempts) {
          this.scheduleReconnect();
        } else if (this.reconnectAttempts >= this.options.maxReconnectAttempts) {
          this.emit('maxReconnectAttemptsReached');
        }
      };
    } catch (error) {
      this.setState(WebSocketState.ERROR);
      this.emit('error', error);
      if (this.options.reconnect) {
        this.scheduleReconnect();
      }
    }
  }

  disconnect(): void {
    if (this.state === WebSocketState.DISCONNECTED) {
      return;
    }

    this.setState(WebSocketState.DISCONNECTING);
    this.options.reconnect = false; // Disable auto-reconnect

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    this.stopHeartbeat();

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.setState(WebSocketState.DISCONNECTED);
    this.emit('disconnect');
  }

  send(message: WebSocketMessage): boolean {
    if (!this.ws || this.state !== WebSocketState.CONNECTED) {
      // Queue message if not connected
      this.messageQueue.push(message);
      return false;
    }

    try {
      this.ws.send(JSON.stringify({
        ...message,
        timestamp: Date.now(),
      }));
      return true;
    } catch (error) {
      this.emit('error', error);
      return false;
    }
  }

  getState(): WebSocketState {
    return this.state;
  }

  isConnected(): boolean {
    return this.state === WebSocketState.CONNECTED;
  }

  private setState(newState: WebSocketState): void {
    if (this.state !== newState) {
      const oldState = this.state;
      this.state = newState;
      this.emit('statechange', { oldState, newState, state: newState });
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      return;
    }

    this.reconnectAttempts++;
    const delay = this.options.reconnectExponentialBackoff
      ? Math.min(this.options.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1), 60000)
      : this.options.reconnectInterval;

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);

    this.emit('reconnect', { attempt: this.reconnectAttempts, delay });
  }

  private startHeartbeat(): void {
    if (this.options.heartbeatInterval <= 0) {
      return;
    }

    this.stopHeartbeat();

    this.heartbeatTimer = setInterval(() => {
      if (this.ws && this.state === WebSocketState.CONNECTED) {
        this.send({ type: 'ping' });
        
        // Set timeout to detect if pong is not received
        this.heartbeatTimeout = setTimeout(() => {
          if (this.ws) {
            console.warn('WebSocket heartbeat timeout, reconnecting...');
            this.ws.close();
          }
        }, 5000);
      }
    }, this.options.heartbeatInterval);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }

    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout);
      this.heartbeatTimeout = null;
    }
  }

  private handleMessage(event: MessageEvent): void {
    try {
      // Handle ping/pong for heartbeat
      if (event.data === 'pong') {
        if (this.heartbeatTimeout) {
          clearTimeout(this.heartbeatTimeout);
          this.heartbeatTimeout = null;
        }
        return;
      }

      const message: WebSocketMessage = JSON.parse(event.data);

      // Handle pong message
      if (message.type === 'pong') {
        if (this.heartbeatTimeout) {
          clearTimeout(this.heartbeatTimeout);
          this.heartbeatTimeout = null;
        }
        return;
      }

      this.emit('message', message);
      this.emit(`message:${message.type}`, message.data);
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
      this.emit('error', error);
    }
  }
}

// Singleton manager for dashboard metrics
let dashboardMetricsManager: WebSocketManager | null = null;

export function getDashboardMetricsWebSocket(): WebSocketManager {
  const baseUrl = getApiBaseUrl();
  
  if (!dashboardMetricsManager) {
    dashboardMetricsManager = new WebSocketManager(baseUrl, {
      path: '/api/ws/dashboard',
      reconnect: true,
      reconnectInterval: 5000,
      maxReconnectAttempts: 10,
      reconnectExponentialBackoff: true,
      heartbeatInterval: 30000,
    });
  }

  return dashboardMetricsManager;
}

// Generic WebSocket manager factory
export function createWebSocketManager(
  path: string,
  options?: WebSocketOptions
): WebSocketManager {
  const baseUrl = getApiBaseUrl();
  return new WebSocketManager(baseUrl, {
    ...options,
    path,
  });
}

export { WebSocketManager };
export default WebSocketManager;
