import { useEffect, useRef, useCallback } from 'react';

interface WebSocketMessage {
  type: 'position_update' | 'item_update' | 'detection_update';
  data: any;
  timestamp: string;
}

interface UseWebSocketOptions {
  url: string;
  onMessage?: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  reconnectInterval?: number;
  enabled?: boolean;
}

export function useWebSocket({
  url,
  onMessage,
  onConnect,
  onDisconnect,
  onError,
  reconnectInterval = 3000,
  enabled = true,
}: UseWebSocketOptions) {
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);
  const shouldReconnect = useRef(true);
  const isConnecting = useRef(false);
  
  // Store callbacks in refs to avoid recreating connect function
  const onMessageRef = useRef(onMessage);
  const onConnectRef = useRef(onConnect);
  const onDisconnectRef = useRef(onDisconnect);
  const onErrorRef = useRef(onError);
  
  useEffect(() => {
    onMessageRef.current = onMessage;
    onConnectRef.current = onConnect;
    onDisconnectRef.current = onDisconnect;
    onErrorRef.current = onError;
  }, [onMessage, onConnect, onDisconnect, onError]);

  const connect = useCallback(() => {
    if (!enabled || ws.current?.readyState === WebSocket.OPEN || isConnecting.current) {
      return;
    }
    if (!enabled || ws.current?.readyState === WebSocket.OPEN) {
      return;
    }

    if (!url) {
      console.error('[WebSocket] Cannot connect: URL is undefined or empty');
      return;
    }

    try {
      console.log(`[WebSocket] Attempting to connect to ${url}...`);
      ws.current = new WebSocket(url);

      ws.current.onopen = () => {
        console.log('[WebSocket] ✅ Connection established successfully');
        shouldReconnect.current = true;
        if (reconnectTimeout.current) {
          clearTimeout(reconnectTimeout.current);
          reconnectTimeout.current = null;
        }
        onConnect?.();
      };

      ws.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          console.log('[WebSocket] 📨 Message received:', message.type, message);
          onMessageRef.current?.(message);
        } catch (error) {
          console.error('[WebSocket] Failed to parse message:', error);
        }
      };

      ws.current.onclose = (event) => {
        console.log('[WebSocket] Disconnected', {
          code: event.code,
          reason: event.reason,
          wasClean: event.wasClean
        });
        onDisconnect?.();
        ws.current = null;

        // Attempt to reconnect if enabled and should reconnect
        if (enabled && shouldReconnect.current && !reconnectTimeout.current) {
          console.log(`[WebSocket] Reconnecting in ${reconnectInterval}ms...`);
          reconnectTimeout.current = setTimeout(() => {
            reconnectTimeout.current = null;
            connect();
          }, reconnectInterval);
        }
      };

      ws.current.onerror = (error) => {
        console.error('[WebSocket] Connection error occurred', {
          type: error.type,
          target: error.target ? 'WebSocket' : undefined,
          readyState: ws.current?.readyState,
          url: url
        });
        onError?.(error);
      };
    } catch (error) {
      console.error('[WebSocket] Failed to create connection:', {
        error: error instanceof Error ? error.message : 'Unknown error',
        url: url
      });
      isConnecting.current = false;
    }
  }, [url, enabled, reconnectInterval]);

  const disconnect = useCallback(() => {
    shouldReconnect.current = false;
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }
    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }
  }, []);

  const send = useCallback((data: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data));
    } else {
      console.warn('[WebSocket] Cannot send message, not connected');
    }
  }, []);

  useEffect(() => {
    if (enabled) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [enabled, connect, disconnect]);

  return {
    send,
    disconnect,
    isConnected: ws.current?.readyState === WebSocket.OPEN,
  };
}
