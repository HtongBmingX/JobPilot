/**
 * useStatus — 定时轮询系统状态
 */
import { ref, onUnmounted } from 'vue'

export function useStatus() {
  const redisConnected = ref(false)

  let timer = null
  const API = ''

  async function fetchStatus() {
    try {
      const res = await fetch(`${API}/status`)
      if (!res.ok) return
      const data = await res.json()
      redisConnected.value = data.redis_connected
    } catch {
      // 静默失败，状态栏显示灰色
    }
  }

  function startPolling(intervalMs = 5000) {
    stopPolling()
    fetchStatus()
    timer = setInterval(fetchStatus, intervalMs)
    // 页面切后台时暂停轮询，切回时恢复（省资源）
    document.addEventListener('visibilitychange', handleVisibility)
  }

  function handleVisibility() {
    if (document.hidden) {
      stopPolling()
    } else if (timer === null) {
      startPolling()
    }
  }

  function stopPolling() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
    document.removeEventListener('visibilitychange', handleVisibility)
  }

  onUnmounted(() => stopPolling())

  return {
    redisConnected, fetchStatus, startPolling, stopPolling,
  }
}
