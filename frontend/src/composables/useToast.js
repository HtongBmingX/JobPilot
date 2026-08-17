/**
 * useToast — 轻量级全局消息提示（替代 alert）
 *
 * 用响应式数组管理 toast 队列，自动消失。非阻塞、样式统一。
 */
import { reactive } from 'vue'

const toasts = reactive([])
let seed = 0

function push(type, message, duration = 3000) {
  const id = ++seed
  toasts.push({ id, type, message })
  if (duration > 0) {
    setTimeout(() => dismiss(id), duration)
  }
  return id
}

function dismiss(id) {
  const idx = toasts.findIndex(t => t.id === id)
  if (idx >= 0) toasts.splice(idx, 1)
}

export function useToast() {
  function success(msg) { return push('success', msg) }
  function error(msg) { return push('error', msg) }
  function info(msg) { return push('info', msg) }

  return { toasts, success, error, info, dismiss }
}
