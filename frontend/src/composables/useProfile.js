/**
 * useProfile — 用户画像管理 Composable
 */
import { ref } from 'vue'

export function useProfile(token) {
  const profile = ref(null)
  const loading = ref(false)

  const API = ''

  function authHeaders() {
    const h = { 'Content-Type': 'application/json' }
    if (token && token.value) h['Authorization'] = `Bearer ${token.value}`
    return h
  }

  /** 拉取画像（不存在则后端创建空画像） */
  async function fetchProfile() {
    loading.value = true
    try {
      const res = await fetch(`${API}/profile`, { headers: authHeaders() })
      if (!res.ok) throw new Error('加载画像失败')
      profile.value = await res.json()
      return profile.value
    } finally {
      loading.value = false
    }
  }

  /** 更新画像 */
  async function updateProfile(updates) {
    const res = await fetch(`${API}/profile`, {
      method: 'PUT',
      headers: authHeaders(),
      body: JSON.stringify(updates),
    })
    if (!res.ok) throw new Error('保存画像失败')
    profile.value = await res.json()
    return profile.value
  }

  return { profile, loading, fetchProfile, updateProfile }
}
