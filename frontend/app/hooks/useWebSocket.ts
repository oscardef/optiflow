'use client';

import { useState, useEffect, useCallback, useRef } from 'react';

// Types for WebSocket messages
export interface PositionUpdate {
  id: number;
  tag_id: string;
  x: number;
  y: number;
  confidence: number;
  num_anchors: number;
  timestamp: string;
}

export interface ItemUpdate {
  rfid_tag: string;
  name: string;
  x: number;
  y: number;
  status: 'present' | 'not present';
  last_seen?: string;
}

export interface ItemStats {
  total: number;
  present: number;
  missing: number;
}

export interface PositionMessage {
  type: 'position_update';
  timestamp: string;
  positions: PositionUpdate[];
}

export interface ItemMessage {
  type: 'item_update';
  timestamp: string;
  items: ItemUpdate[];
  stats: ItemStats;
}

export interface CombinedMessage {
  timestamp: string;
  updates: (PositionMessage | ItemMessage)[];
}

export type WebSocketMessage = PositionMessage | ItemMessage | CombinedMessage;

export interface UseWebSocketOptions {
  url: string;
  onPositionUpdate?: (positions: PositionUpdate[]) => void;
  onItemUpdate?: (items: ItemUpdate[], stats: ItemStats) => void;
  onError?: (error: Event) => void;
  onOpen?: () => void;
  onClose?: () => void;
  reconnectAttempts?: number;
  reconnectInterval?: number;
}

export interface UseWebSocketReturn {
  isConnected: boolean;
  error: Event | null;
  reconnect: () => void;
  disconnect: () => void;
  latestPositions: PositionUpdate[];
  latestItems: ItemUpdate[];
  itemStats: ItemStats | null;
}

/**
 * Custom hook for WebSocket connection to OptiFlow backend
 * Provides real-time position and item updates
 */
export function useWebSocket(options: UseWebSocketOptions): UseWebSocketReturn {
  const {
    url,
    onPositionUpdate,
    onItemUpdate,
    onError,
    onOpen,
    onClose,
    reconnectAttempts = 5,
    reconnectInterval = 3000,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Event | null>(null);
  const [latestPositions, setLatestPositions] = useState<PositionUpdate[]>([]);
  const [latestItems, setLatestItems] = useState<ItemUpdate[]>([]);
  const [itemStats, setItemStats] = useState<ItemStats | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        setIsConnected(true);
        setError(null);
        reconnectCountRef.current = 0;
        onOpen?.();
      };

      ws.onclose = () => {
        setIsConnected(false);
        onClose?.();

        // Auto-reconnect logic
        if (reconnectCountRef.current < reconnectAttempts) {
          reconnectCountRef.current += 1;
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        }
      };

      ws.onerror = (event) => {
        setError(event);
        onError?.(event);
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);

          // Handle different message types
          if ('type' in message) {
            if (message.type === 'position_update') {
              setLatestPositions(message.positions);
              onPositionUpdate?.(message.positions);
            } else if (message.type === 'item_update') {
              setLatestItems(message.items);
              setItemStats(message.stats);
              onItemUpdate?.(message.items, message.stats);
            }
          } else if ('updates' in message) {
            // Combined message
            for (const update of message.updates) {
              if (update.type === 'position_update') {
                setLatestPositions(update.positions);
                onPositionUpdate?.(update.positions);
              } else if (update.type === 'item_update') {
                setLatestItems(update.items);
                setItemStats(update.stats);
                onItemUpdate?.(update.items, update.stats);
              }
            }
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      wsRef.current = ws;
    } catch (e) {
      console.error('Failed to create WebSocket connection:', e);
    }
  }, [url, onPositionUpdate, onItemUpdate, onError, onOpen, onClose, reconnectAttempts, reconnectInterval]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    reconnectCountRef.current = reconnectAttempts; // Prevent auto-reconnect
    wsRef.current?.close();
    wsRef.current = null;
    setIsConnected(false);
  }, [reconnectAttempts]);

  const reconnect = useCallback(() => {
    disconnect();
    reconnectCountRef.current = 0;
    connect();
  }, [connect, disconnect]);

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected,
    error,
    reconnect,
    disconnect,
    latestPositions,
    latestItems,
    itemStats,
  };
}

/**
 * Hook for position-only WebSocket updates
 */
export function usePositionWebSocket(
  backendUrl: string = 'ws://localhost:8000',
  onUpdate?: (positions: PositionUpdate[]) => void
): UseWebSocketReturn {
  return useWebSocket({
    url: `${backendUrl}/ws/positions`,
    onPositionUpdate: onUpdate,
  });
}

/**
 * Hook for item-only WebSocket updates
 */
export function useItemWebSocket(
  backendUrl: string = 'ws://localhost:8000',
  onUpdate?: (items: ItemUpdate[], stats: ItemStats) => void
): UseWebSocketReturn {
  return useWebSocket({
    url: `${backendUrl}/ws/items`,
    onItemUpdate: onUpdate,
  });
}

/**
 * Hook for combined WebSocket updates (positions + items)
 */
export function useCombinedWebSocket(
  backendUrl: string = 'ws://localhost:8000',
  onPositionUpdate?: (positions: PositionUpdate[]) => void,
  onItemUpdate?: (items: ItemUpdate[], stats: ItemStats) => void
): UseWebSocketReturn {
  return useWebSocket({
    url: `${backendUrl}/ws/combined`,
    onPositionUpdate,
    onItemUpdate,
  });
}

export default useWebSocket;
