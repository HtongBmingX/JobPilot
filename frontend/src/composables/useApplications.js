/**
 * useApplications — 投递记录管理 Composable
 */
import { ref } from 'vue'

export function useApplications(token) {
  const apps = ref([])
  const appsLoading = ref(false)
  const appsError = ref('')

  const API = ''

  function authHeaders() {
    const h = { 'Content-Type': 'application/json' }
    if (token && token.value) h['Authorization'] = `Bearer ${token.value}`
    return h
  }

  /** 拉取投递列表 */
  async function fetchApps(status = null) {
    appsLoading.value = true
    appsError.value = ''
    try {
      let url = `${API}/applications`
      if (status) url += `?status=${status}`
      const res = await fetch(url, { headers: authHeaders() })
      if (!res.ok) throw new Error('加载失败')
      apps.value = await res.json()
    } catch (e) {
      appsError.value = e.message
      // 抛出给调用方（App.vue）用 toast 展示
      throw e
    } finally {
      appsLoading.value = false
    }
  }

  /** 创建投递记录 */
  async function createApp(data) {
    const res = await fetch(`${API}/applications`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(data),
    })
    if (!res.ok) throw new Error('保存失败')
    const app = await res.json()
    apps.value.unshift(app)  // 插到列表最前面
    return app
  }

  /** 更新状态 */
  async function updateApp(id, updates) {
    const res = await fetch(`${API}/applications/${id}`, {
      method: 'PUT',
      headers: authHeaders(),
      body: JSON.stringify(updates),
    })
    if (!res.ok) throw new Error('更新失败')
    const updated = await res.json()
    const idx = apps.value.findIndex(a => a.id === id)
    if (idx >= 0) apps.value[idx] = updated
    return updated
  }

  /** 删除 */
  async function deleteApp(id) {
    const res = await fetch(`${API}/applications/${id}`, {
      method: 'DELETE',
      headers: authHeaders(),
    })
    if (!res.ok) throw new Error('删除失败')
    apps.value = apps.value.filter(a => a.id !== id)
  }

  return { apps, appsLoading, appsError, fetchApps, createApp, updateApp, deleteApp }
}
