/**
 * WebSocket hook for real-time data streaming
 */

import { useEffect, useRef, useState, useCallback } from 'react';

function normalizeWebSocketBaseUrl(value?: string | null): string | null {
  if (!value) return null;

  const trimmed = value.trim();
  if (!trimmed) return null;

  const withProtocol = /^[a-z]+:\/\//i.test(trimmed)
    ? trimmed
    : `https://${trimmed.replace(/^\/+/, '')}`;

  try {
    const parsed = new URL(withProtocol);
    const protocol = parsed.protocol.toLowerCase();
    const wsProtocol =
      protocol === 'http:' || protocol === 'ws:'
        ? 'ws:'
        : protocol === 'https:' || protocol === 'wss:'
          ? 'wss:'
          : null;
    if (!wsProtocol) return null;
    return `${wsProtocol}//${parsed.host}`;
  } catch {
    return null;
  }
}

// Dynamically determine WebSocket base URL (env > current host fallback)
function getWebSocketBaseUrl(): string {
  const explicitWsUrl = normalizeWebSocketBaseUrl(process.env.NEXT_PUBLIC_WS_URL);
  if (explicitWsUrl) return explicitWsUrl;

  const apiWsUrl = normalizeWebSocketBaseUrl(process.env.NEXT_PUBLIC_API_URL);
  if (apiWsUrl) return apiWsUrl;

  if (typeof window !== 'undefined') {
    const { hostname, host, protocol } = window.location;
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return `ws://${hostname}:8000`;
    }
    const wsProtocol = protocol === 'https:' ? 'wss:' : 'ws:';
    return `${wsProtocol}//${host}`;
  }

  return 'ws://localhost:8000';
}

function getWebSocketStreamUrl(): string {
  return `${getWebSocketBaseUrl()}/api/v1/ws/stream`;
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
      const wsUrl = getWebSocketStreamUrl();
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
    isReal: boolean;
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
          isReal?: boolean;
        };
        setPrices((prev) => ({
          ...prev,
          [priceData.symbol]: {
            bid: priceData.bid,
            ask: priceData.ask,
            mid: priceData.mid,
            spread: priceData.spread,
            timestamp: priceData.timestamp,
            isReal: priceData.isReal ?? false,
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

/**
 * Hook for getting available symbols from broker
 * Returns only symbols that have real broker prices (not simulated)
 */
export function useAvailableSymbols() {
  const [availableSymbols, setAvailableSymbols] = useState<string[]>([]);
  const [failedSymbols, setFailedSymbols] = useState<string[]>([]);
  const [brokerConnected, setBrokerConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const connect = () => {
      try {
        const wsUrl = getWebSocketStreamUrl();
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          // Request available symbols
          ws.send(JSON.stringify({ action: 'get_available_symbols' }));
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'available_symbols') {
              setAvailableSymbols(data.available || []);
              setFailedSymbols(data.failed || []);
              setBrokerConnected(data.broker_connected || false);
            }
          } catch (err) {
            console.error('Failed to parse available symbols:', err);
          }
        };

        ws.onclose = () => {
          // Reconnect after 5 seconds
          setTimeout(connect, 5000);
        };
      } catch (err) {
        console.error('Failed to connect for available symbols:', err);
      }
    };

    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return { availableSymbols, failedSymbols, brokerConnected };
}

export default useWebSocket;
