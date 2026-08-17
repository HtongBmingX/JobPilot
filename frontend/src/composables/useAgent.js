import { ref } from 'vue'

/**
 * useAgent — 封装 Agent 交互 + JWT 鉴权 + 多会话管理 的 Composable
 *
 * 多会话存储结构（localStorage）：
 *   jp_conversations = [
 *     { id, title, messages: [{role, content, isMarkdown}], updatedAt },
 *     ...
 *   ]
 *   jp_active_conversation = 当前会话 id
 *   jp_agent_mode = 'handwritten' | 'langchain'
 */
const STORAGE_CONVERSATIONS = 'jp_conversations'
const STORAGE_ACTIVE = 'jp_active_conversation'
const STORAGE_AGENT_MODE = 'jp_agent_mode'

export function useAgent() {
  // ---- 鉴权状态 ----
  const token = ref(null)
  const refreshToken = ref(null)
  const username = ref('')
  const isLoggedIn = ref(false)

  // ---- 多会话状态 ----
  const conversations = ref([])   // 会话列表（含 messages）
  const activeId = ref(null)      // 当前会话 id
  const agentMode = ref(localStorage.getItem(STORAGE_AGENT_MODE) || 'handwritten')

  // ---- 当前会话的对话状态 ----
  const messages = ref([])        // 当前会话的消息（从 conversations 里派生）
  const thinkSteps = ref([])
  const loading = ref(false)
  const error = ref('')

  const API = ''

  // 用于取消正在进行的流式请求
  let _abortController = null

  // ============================================================
  //  会话持久化
  // ============================================================
  function _persist() {
    try {
      localStorage.setItem(STORAGE_CONVERSATIONS, JSON.stringify(conversations.value))
      if (activeId.value) localStorage.setItem(STORAGE_ACTIVE, activeId.value)
      localStorage.setItem(STORAGE_AGENT_MODE, agentMode.value)
    } catch { /* localStorage 满了就静默失败 */ }
  }

  function _loadFromLocal() {
    try {
      const raw = localStorage.getItem(STORAGE_CONVERSATIONS)
      if (raw) conversations.value = JSON.parse(raw) || []
      const active = localStorage.getItem(STORAGE_ACTIVE)
      if (active && conversations.value.some(c => c.id === active)) {
        activeId.value = active
      } else if (conversations.value.length) {
        activeId.value = conversations.value[0].id
      }
      agentMode.value = localStorage.getItem(STORAGE_AGENT_MODE) || 'handwritten'
    } catch {
      conversations.value = []
    }
  }

  /** 当前会话对象（派生） */
  function _activeConv() {
    return conversations.value.find(c => c.id === activeId.value) || null
  }

  /** 把当前会话的 messages 同步到响应式 messages */
  function _syncMessages() {
    const conv = _activeConv()
    messages.value = conv ? [...conv.messages] : []
  }

  /** 新建会话，返回新会话 id */
  function newConversation() {
    const id = 'conv_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8)
    conversations.value.unshift({
      id,
      title: '新对话',
      messages: [],
      updatedAt: Date.now(),
    })
    activeId.value = id
    thinkSteps.value = []
    error.value = ''
    _syncMessages()
    _persist()
    return id
  }

  /** 切换到某个会话 */
  function switchConversation(id) {
    if (!conversations.value.some(c => c.id === id)) return
    // 切换前中断进行中的请求，避免旧会话的流继续污染新会话
    if (_abortController) {
      _abortController.abort()
      _abortController = null
    }
    activeId.value = id
    thinkSteps.value = []
    error.value = ''
    loading.value = false
    _syncMessages()
    _persist()
  }

  /** 删除会话 */
  function deleteConversation(id) {
    conversations.value = conversations.value.filter(c => c.id !== id)
    if (activeId.value === id) {
      activeId.value = conversations.value.length ? conversations.value[0].id : null
    }
    thinkSteps.value = []
    error.value = ''
    loading.value = false
    _syncMessages()
    _persist()
  }

  /** 根据首条用户消息自动生成会话标题 */
  function _autoTitle(query) {
    const clean = query.replace(/\s+/g, ' ').trim()
    if (clean.length <= 20) return clean
    return clean.slice(0, 20) + '…'
  }

  // 初始加载
  _loadFromLocal()
  _syncMessages()

  // ============================================================
  //  鉴权方法
  // ============================================================

  /** 注册新用户 */
  async function register(user, pass) {
    error.value = ''
    const res = await fetch(`${API}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: user, password: pass }),
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || `注册失败（${res.status}）`)
    }
    await login(user, pass)
  }

  /** 登录 */
  async function login(user, pass) {
    error.value = ''
    const res = await fetch(`${API}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: user, password: pass }),
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || `登录失败（${res.status}）`)
    }
    const data = await res.json()
    token.value = data.access_token
    refreshToken.value = data.refresh_token
    username.value = user
    isLoggedIn.value = true
    console.log('[useAgent] 登录成功')
  }

  /** 退出登录 */
  function logout() {
    token.value = null
    refreshToken.value = null
    username.value = ''
    isLoggedIn.value = false
    conversations.value = []
    activeId.value = null
    messages.value = []
    thinkSteps.value = []
    try {
      localStorage.removeItem(STORAGE_CONVERSATIONS)
      localStorage.removeItem(STORAGE_ACTIVE)
      localStorage.removeItem(STORAGE_AGENT_MODE)  // 清除 agent 模式，避免跨用户残留
    } catch { /* ignore */ }
  }

  // ============================================================
  //  工具函数
  // ============================================================

  function authHeaders() {
    const h = { 'Content-Type': 'application/json' }
    if (token.value) h['Authorization'] = `Bearer ${token.value}`
    return h
  }

  // ============================================================
  //  文件上传
  // ============================================================

  async function uploadFile(file) {
    error.value = ''
    const form = new FormData()
    form.append('file', file)

    loading.value = true
    try {
      const h = {}
      if (token.value) h['Authorization'] = `Bearer ${token.value}`
      const res = await fetch(`${API}/upload`, { method: 'POST', body: form, headers: h })
      if (!res.ok) {
        // 尝试解析后端返回的具体错误信息（如扫描件检测提示）
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || `上传失败：HTTP ${res.status}`)
      }
      const data = await res.json()
      return data.text
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  // ============================================================
  //  发送消息（流式）
  // ============================================================

  async function sendMessage(query, { resumeText, jdText } = {}) {
    error.value = ''
    if (!query.trim()) return

    // 没有当前会话时自动创建一个
    if (!_activeConv()) {
      newConversation()
    }

    loading.value = true
    thinkSteps.value = []

    // 首条用户消息 → 自动生成标题
    const conv = _activeConv()
    if (conv && conv.messages.length === 0) {
      conv.title = _autoTitle(query)
    }

    // 只在这里 push 一次用户消息和空 assistant 消息（401 重试不重复 push）
    conv.messages.push({ role: 'user', content: query })
    conv.updatedAt = Date.now()
    messages.value = [...conv.messages]
    const assistantMsg = { role: 'assistant', content: '', isMarkdown: true }
    conv.messages.push(assistantMsg)
    messages.value = [...conv.messages]

    // 内部函数：发请求 + 消费 SSE 流（401 刷新后重试它，不重试整个 sendMessage）
    async function _doStream() {
      const endpoint = agentMode.value === 'langchain'
        ? `${API}/agent/langchain/stream`
        : `${API}/agent/run/stream`

      _abortController = new AbortController()
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: authHeaders(),
        signal: _abortController.signal,
        body: JSON.stringify({
          query,
          resume: resumeText || null,
          jd: jdText || null,
          session_id: activeId.value || null,
        }),
      })

      if (res.status === 401) {
        const refreshed = await tryRefreshToken()
        if (refreshed) {
          // 刷新成功，重试请求（消息已 push 过，不会重复）
          return await _doStream()
        }
        logout()
        error.value = '登录已过期，请重新登录'
        return
      }

      if (!res.ok) {
        const errText = await res.text()
        let errMsg = `请求失败：HTTP ${res.status}`
        try {
          const parsed = JSON.parse(errText)
          errMsg = parsed.message || parsed.detail || errMsg
        } catch {
          errMsg += ` - ${errText.slice(0, 100)}`
        }
        throw new Error(errMsg)
      }

      // 消费 SSE 流
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split('\n\n')
        buffer = parts.pop()

        for (const part of parts) {
          if (!part.trim()) continue
          const { eventType, data } = parseSSEMessage(part)
          if (!eventType || !data) continue

          switch (eventType) {
            case 'step_start':
              thinkSteps.value.push({ step: data.step, thought: data.thought || '', status: 'running' })
              break
            case 'step_done': {
              const found = thinkSteps.value.find(s => s.step === data.step && s.status === 'running')
              if (found) found.status = 'done'
              break
            }
            case 'synthesize_chunk':
              assistantMsg.content += data.text
              messages.value = [...conv.messages.slice(0, -1), { ...assistantMsg }]
              break
            case 'done':
              conv.messages = messages.value
              conv.updatedAt = Date.now()
              _persist()
              break
            case 'error':
              error.value = data.message || '未知错误'
              break
          }
        }
      }
    }

    try {
      await _doStream()
    } catch (e) {
      if (e.name === 'AbortError') {
        console.warn('[useAgent] 请求被用户取消')
        error.value = ''
      } else if (e.message.includes('HTTP 502')) {
        error.value = 'AI 服务暂时不可用，请稍后重试 | ' + e.message
      } else {
        error.value = e.message || '未知错误'
      }
      // 流中断但用户消息已发，保留；空助手消息则移除
      if (assistantMsg && !assistantMsg.content) {
        const idx = conv.messages.indexOf(assistantMsg)
        if (idx >= 0) conv.messages.splice(idx, 1)
        messages.value = [...conv.messages]
      }
    } finally {
      _abortController = null
      _persist()
      loading.value = false
    }
  }

  /** 停止当前正在生成的回复 */
  function stopGenerating() {
    if (_abortController) {
      _abortController.abort()
      _abortController = null
    }
  }

  /** 尝试用 refresh_token 自动续期 */
  async function tryRefreshToken() {
    if (!refreshToken.value) return false
    try {
      const res = await fetch(`${API}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken.value }),
      })
      if (!res.ok) return false
      const data = await res.json()
      token.value = data.access_token
      refreshToken.value = data.refresh_token
      return true
    } catch {
      return false
    }
  }

  return {
    // 鉴权
    token, username, isLoggedIn,
    register, login, logout,
    // 多会话
    conversations, activeId,
    newConversation, switchConversation, deleteConversation,
    // 对话
    messages, thinkSteps, loading, error, agentMode,
    uploadFile, sendMessage, stopGenerating,
  }
}

function parseSSEMessage(raw) {
  let eventType = ''
  let dataStr = ''
  for (const line of raw.split('\n')) {
    if (line.startsWith('event: ')) eventType = line.slice(7).trim()
    else if (line.startsWith('data: ')) dataStr = line.slice(6).trim()
  }
  if (!dataStr) return { eventType: '', data: null }
  let data = null
  try { data = JSON.parse(dataStr) } catch { /* skip */ }
  return { eventType, data }
}
