import { describe, it, expect, vi, beforeEach } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { useWebSocket } from '../useWebSocket'

vi.mock('../../services/websocketService', () => ({
  createWebSocket: vi.fn() as any,
})) as any

import { createWebSocket } from '../../services/websocketService'

describe('useWebSocket', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should return isConnected false initially', () => {
    const mockSocket = { readyState: 1, close: vi.fn() } as any
    vi.mocked(createWebSocket).mockReturnValue(mockSocket)

    const { result } = renderHook(() => useWebSocket(() => {}, () => {}))

    expect(createWebSocket).toHaveBeenCalled()
    expect(result.current.isConnected).toBe(false)
  })

  it('should return a reconnect function', () => {
    const mockSocket = { readyState: 1, close: vi.fn() } as any
    vi.mocked(createWebSocket).mockReturnValue(mockSocket)

    const { result } = renderHook(() => useWebSocket(() => {}, () => {}))

    expect(typeof result.current.reconnect).toBe('function')
  })

  it('should pass onError callback when error occurs', () => {
    const mockSocket = { readyState: 1, close: vi.fn() } as any
    let capturedErrorCallback: any

    vi.mocked(createWebSocket).mockImplementation((_onMsg, onErr, _onOpen, _onClose) => {
      capturedErrorCallback = onErr
      return mockSocket
    })

    const onError = vi.fn()
    renderHook(() => useWebSocket(() => {}, onError))

    expect(typeof capturedErrorCallback).toBe('function')

    act(() => {
      capturedErrorCallback({ message: 'Connection failed' })
    })

    expect(onError).toHaveBeenCalledWith({ message: 'Connection failed' })
  })
})