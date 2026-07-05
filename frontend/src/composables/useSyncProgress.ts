import { onBeforeUnmount, ref } from 'vue'
import type { SyncProgress } from '../api/types'

export function useSyncProgress() {
  const progress = ref<SyncProgress | null>(null)
  const connected = ref(false)
  let socket: WebSocket | null = null

  function connect() {
    if (socket) return
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const wsHost = window.location.port === '5173' ? '127.0.0.1:8000' : window.location.host
    socket = new WebSocket(`${protocol}://${wsHost}/api/sync/progress`)
    socket.onopen = () => {
      connected.value = true
    }
    socket.onmessage = (event) => {
      progress.value = JSON.parse(event.data) as SyncProgress
    }
    socket.onerror = () => {
      connected.value = false
    }
    socket.onclose = () => {
      connected.value = false
      socket = null
    }
  }

  function disconnect() {
    socket?.close()
    socket = null
    connected.value = false
  }

  onBeforeUnmount(disconnect)

  return { progress, connected, connect, disconnect }
}
