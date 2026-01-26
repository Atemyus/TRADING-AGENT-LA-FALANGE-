/**
 * WebSocket hook for real-time data streaming
 */

import { useEffect, useRef, useState, useCallback } from 'react';

// Production backend URL (Railway)
const PRODUCTION_BACKEND_URL = 'wss://trading-agent-la-falange-production.up.railway.app';

// Dynamically determine WebSocket URL based on current page location or API URL
function getWebSocketUrl(): string {
  // First check environment variable
  if (process.env.NEXT_PUBLIC_WS_URL) {
    return process.env.NEXT_PUBLIC_WS_URL;
  }

  // Check if API URL is set and derive WS URL from it
  if (process.env.NEXT_PUBLIC_API_URL) {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    // Convert http(s) to ws(s)
    return apiUrl.replace(/^http/, 'ws');
  }

  // If running in browser, derive from current location
  if (typeof window !== 'undefined') {
    const host = window.location.host;

    // If we're on localhost, use local backend
    if (host.includes('localhost') || host.includes('127.0.0.1')) {
      const hostname = window.location.hostname;
      return `ws://${hostname}:8000`;
    }

    // For production (Railway, etc.), use the hardcoded production URL
    return PRODUCTION_BACKEND_URL;
  }

  // Fallback for SSR - use production URL
  return PRODUCTION_BACKEND_URL;
}

// Get URL once at module load time
let WS_URL = PRODUCTION_BACKEND_URL;
if (typeof window !== 'undefined') {
  WS_URL = getWebSocketUrl();
  console.log('[WebSocket] Using URL:', WS_URL);
}

type MessageHandler = (data: unknown) => void;

interface UseWebSocketOptions {
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  reconnectAttempts?: number;
  reconnectInterval?: number;
}

interface UseWebSocketReturn {
  isConnected: boolean;
  subscribe: (channel: string, symbols?: string[]) => void;
  unsubscribe: (channel: string) => void;
  addMessageHandler: (type: string, handler: MessageHandler) => void;
  removeMessageHandler: (type: string) => void;
}

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const {
    onOpen,
    onClose,
    onError,
    reconnectAttempts = 5,
    reconnectInterval = 3000,
  } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const handlersRef = useRef<Map<string, MessageHandler>>(new Map());
  const reconnectCountRef = useRef(0);
  const [isConnected, setIsConnected] = useState(false);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      const wsUrl = `${WS_URL}/api/v1/ws/stream`;
      console.log('[WebSocket] Connecting to:', wsUrl);
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setIsConnected(true);
        reconnectCountRef.current = 0;
        onOpen?.();
      };

      ws.onclose = () => {
        setIsConnected(false);
        onClose?.();

        // Attempt reconnection
        if (reconnectCountRef.current < reconnectAttempts) {
          reconnectCountRef.current++;
          setTimeout(connect, reconnectInterval);
        }
      };

      ws.onerror = (error) => {
        onError?.(error);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const handler = handlersRef.current.get(data.type);
          if (handler) {
            handler(data);
          }
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      wsRef.current = ws;
    } catch (err) {
      console.error('Failed to connect WebSocket:', err);
    }
  }, [onOpen, onClose, onError, reconnectAttempts, reconnectInterval]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const subscribe = useCallback((channel: string, symbols?: string[]) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          action: 'subscribe',
          channel,
          ...(symbols && { symbols }),
        })
      );
    }
  }, []);

  const unsubscribe = useCallback((channel: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          action: 'unsubscribe',
          channel,
        })
      );
    }
  }, []);

  const addMessageHandler = useCallback((type: string, handler: MessageHandler) => {
    handlersRef.current.set(type, handler);
  }, []);

  const removeMessageHandler = useCallback((type: string) => {
    handlersRef.current.delete(type);
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return {
    isConnected,
    subscribe,
    unsubscribe,
    addMessageHandler,
    removeMessageHandler,
  };
}

/**
 * Hook for subscribing to price updates
 */
export function usePriceStream(symbols: string[]) {
  const [prices, setPrices] = useState<Record<string, {
    bid: string;
    ask: string;
    mid: string;
    spread: string;
    timestamp: string;
  }>>({});

  const { isConnected, subscribe, addMessageHandler, removeMessageHandler } = useWebSocket();

  useEffect(() => {
    if (isConnected && symbols.length > 0) {
      subscribe('prices', symbols);

      addMessageHandler('price', (data: unknown) => {
        const priceData = data as {
          symbol: string;
          bid: string;
          ask: string;
          mid: string;
          spread: string;
          timestamp: string;
        };
        setPrices((prev) => ({
          ...prev,
          [priceData.symbol]: {
            bid: priceData.bid,
            ask: priceData.ask,
            mid: priceData.mid,
            spread: priceData.spread,
            timestamp: priceData.timestamp,
          },
        }));
      });

      return () => {
        removeMessageHandler('price');
      };
    }
  }, [isConnected, symbols, subscribe, addMessageHandler, removeMessageHandler]);

  return { prices, isConnected };
}

/**
 * Hook for subscribing to position updates
 */
interface PositionData {
  symbol: string;
  [key: string]: unknown;
}

export function usePositionStream() {
  const [positions, setPositions] = useState<PositionData[]>([]);
  const { isConnected, subscribe, addMessageHandler, removeMessageHandler } = useWebSocket();

  useEffect(() => {
    if (isConnected) {
      subscribe('positions');

      addMessageHandler('position', (data: unknown) => {
        const positionData = data as { data: PositionData };
        setPositions((prev) => {
          // Update or add position
          const updated = [...prev];
          const existingIndex = updated.findIndex(
            (p) => p.symbol === positionData.data.symbol
          );
          if (existingIndex >= 0) {
            updated[existingIndex] = positionData.data;
          } else {
            updated.push(positionData.data);
          }
          return updated;
        });
      });

      return () => {
        removeMessageHandler('position');
      };
    }
  }, [isConnected, subscribe, addMessageHandler, removeMessageHandler]);

  return { positions, isConnected };
}

export default useWebSocket;
