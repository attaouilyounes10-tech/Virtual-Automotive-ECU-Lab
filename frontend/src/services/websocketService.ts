export function createWebSocket(
  onMessage: (data: any) => void,
  onError?: (err: any) => void,
  onOpen?: () => void,
  onClose?: () => void
): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const wsUrl = `${protocol}//${host}/api/ws/live`

  const socket = new WebSocket(wsUrl)

  socket.addEventListener('open', () => {
    console.log('[WebSocket] Connecté à', wsUrl)
    onOpen?.()
  })

  socket.addEventListener('message', (event) => {
    try {
      const data = JSON.parse(event.data)
      onMessage(data)
    } catch (e) {
      console.error('[WebSocket] Erreur de parsing:', e)
    }
  })

  socket.addEventListener('error', (err) => {
    console.error('[WebSocket] Erreur:', err)
    onError?.(err)
  })

  socket.addEventListener('close', () => {
    console.log('[WebSocket] Déconnecté')
    onClose?.()
  })

  return socket
}