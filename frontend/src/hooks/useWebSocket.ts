import { useRef, useEffect, useState, useCallback } from 'react'
import { createWebSocket } from '../services/websocketService'

export function useWebSocket(
  onMessage: (data: any) => void,
  onError?: (err: any) => void
) {
  const socketRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number | null>(null)
  const [isConnected, setIsConnected] = useState(false)

  const connect = useCallback(() => {
    if (socketRef.current?.readyState === WebSocket.OPEN) return

    socketRef.current = createWebSocket(
      (data) => {
        setIsConnected(true)
        onMessage(data)
      },
      (err) => {
        setIsConnected(false)
        onError?.(err)
        if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = window.setTimeout(connect, 3000)
      },
      () => setIsConnected(true),
      () => setIsConnected(false)
    )
  }, [onMessage, onError])

  useEffect(() => {
    connect()
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current)
      socketRef.current?.close()
      socketRef.current = null
      setIsConnected(false)
    }
  }, [connect])

  return { isConnected, reconnect: connect }
}