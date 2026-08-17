/**
 * useResumes — 简历库管理 Composable
 */
import { ref } from 'vue'

export function useResumes(token) {
  const resumes = ref([])
  const loading = ref(false)
  const error = ref('')

  const API = ''

  function authHeaders() {
    const h = { 'Content-Type': 'application/json' }
    if (token && token.value) h['Authorization'] = `Bearer ${token.value}`
    return h
  }

  /** 拉取简历列表 */
  async function fetchResumes() {
    loading.value = true
    error.value = ''
    try {
      const res = await fetch(`${API}/resumes`, { headers: authHeaders() })
      if (!res.ok) throw new Error('加载简历失败')
      resumes.value = await res.json()
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  /** 保存当前简历到简历库 */
  async function saveResume(name, content, isDefault = false) {
    const res = await fetch(`${API}/resumes`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ name, content, is_default: isDefault }),
    })
    if (!res.ok) throw new Error('保存简历失败')
    const resume = await res.json()
    resumes.value.unshift(resume)  // 新简历插到最前面（与 createApp 一致）
    return resume
  }

  /** 删除简历 */
  async function deleteResume(id) {
    const res = await fetch(`${API}/resumes/${id}`, {
      method: 'DELETE',
      headers: authHeaders(),
    })
    if (!res.ok) throw new Error('删除简历失败')
    resumes.value = resumes.value.filter(r => r.id !== id)
  }

  return { resumes, loading, error, fetchResumes, saveResume, deleteResume }
}
