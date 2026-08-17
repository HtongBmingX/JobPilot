<script setup>
import { ref, nextTick, onMounted, watch } from 'vue'
import { useAgent } from './composables/useAgent.js'
import { useApplications } from './composables/useApplications.js'
import { useStatus } from './composables/useStatus.js'
import { useToast } from './composables/useToast.js'
import { useResumes } from './composables/useResumes.js'
import { useProfile } from './composables/useProfile.js'
import ChatBubble from './components/ChatBubble.vue'
import ThinkChain from './components/ThinkChain.vue'
import InputPanel from './components/InputPanel.vue'
import JobBoard from './components/JobBoard.vue'
import StatusBar from './components/StatusBar.vue'
import ConversationSidebar from './components/ConversationSidebar.vue'
import ToastContainer from './components/ToastContainer.vue'
import ProfileModal from './components/ProfileModal.vue'
import AboutView from './components/AboutView.vue'

const {
  // 鉴权
  username, isLoggedIn, token,
  register, login, logout,
  // 多会话
  conversations, activeId,
  newConversation, switchConversation, deleteConversation,
  // 对话
  messages, thinkSteps, loading, error,
  uploadFile, sendMessage, stopGenerating, agentMode,
} = useAgent()

// ---- 全局 toast ----
const toast = useToast()

// ---- 投递看板 ----
const { apps, appsLoading, appsError, fetchApps, createApp, updateApp, deleteApp } = useApplications(token)

// ---- 简历库 ----
const { resumes, fetchResumes, saveResume, deleteResume } = useResumes(token)

// ---- 用户画像 ----
const { profile, fetchProfile, updateProfile, loading: profileLoading } = useProfile(token)

// ---- 系统状态栏 ----
const { redisConnected, startPolling, stopPolling } = useStatus()

onMounted(() => {
  if (isLoggedIn.value) {
    fetchApps().catch(() => {})
    fetchResumes().catch(() => {})
    startPolling()
  }
})

watch(isLoggedIn, (val) => {
  if (val) startPolling()
  else stopPolling()
})

// ---- 登录表单状态 ----
const authMode = ref('login')
const authUser = ref('')
const authPass = ref('')
const authError = ref('')
const authLoading = ref(false)

async function handleAuth() {
  authError.value = ''
  if (!authUser.value.trim() || !authPass.value.trim()) {
    authError.value = '请填写用户名和密码'
    return
  }
  authLoading.value = true
  try {
    if (authMode.value === 'register') {
      await register(authUser.value, authPass.value)
    } else {
      await login(authUser.value, authPass.value)
    }
    fetchApps().catch(() => {})
  } catch (e) {
    authError.value = e.message
  } finally {
    authLoading.value = false
  }
}

// ---- 聊天状态 ----
const resumeText = ref('')
const jdText = ref('')
const query = ref('')
const fileName = ref('')
const uploading = ref(false)
const chatArea = ref(null)

function scrollToBottom() {
  nextTick(() => {
    if (chatArea.value) {
      chatArea.value.scrollTop = chatArea.value.scrollHeight
    }
  })
}

async function handleUpload(event) {
  const file = event.target.files[0]
  if (!file) return
  uploading.value = true
  try {
    const text = await uploadFile(file)
    fileName.value = file.name
    resumeText.value = text
    toast.success('简历解析成功')
  } catch (e) {
    toast.error(e.message)
    // 重置文件选择，允许用户重新选择同一个文件
    if (event.target) event.target.value = ''
  } finally {
    uploading.value = false
  }
}

function handleRun() {
  if (!query.value.trim() || loading.value) return

  // 发送前校验：只在"首次分析"请求且确实无内容时提醒。
  // 匹配/契合/对比/追问类请求依赖后端缓存的已有分析结果，输入框为空是正常的，不提醒。
  const q = query.value
  const isMatchRequest = /匹配|契合|适合|对比|差距|match/i.test(q)
  if (!isMatchRequest) {
    const asksResumeAnalysis = /分析.*简历|简历.*分析|优化简历|看看简历/.test(q)
    const asksJdAnalysis = /分析.*(jd|岗位|职位)|jd.*分析|岗位要求|岗位职责|岗位描述/.test(q)
    if (asksResumeAnalysis && !resumeText.value.trim()) {
      toast.info('提示：要分析简历，请先上传或粘贴简历内容')
    }
    if (asksJdAnalysis && !jdText.value.trim()) {
      toast.info('提示：要分析 JD，请先粘贴岗位描述')
    }
  }

  const currentQuery = query.value
  const currentResume = resumeText.value
  const currentJd = jdText.value
  query.value = ''
  sendMessage(currentQuery, { resumeText: currentResume, jdText: currentJd })
  scrollToBottom()
}

async function handleSaveToBoard(data) {
  try {
    await createApp(data)
    toast.success('已保存到投递看板')
  } catch (e) {
    toast.error('保存失败：' + e.message)
  }
}

// ---- 简历库 ----
async function handleSaveResume(name) {
  if (!resumeText.value.trim()) {
    toast.error('简历内容为空，无法保存')
    return
  }
  try {
    await saveResume(name || '我的简历', resumeText.value)
    toast.success('已保存到简历库')
  } catch (e) {
    toast.error('保存简历失败：' + e.message)
  }
}

async function handleLoadResume(id) {
  const r = resumes.value.find(x => x.id === id)
  if (r) {
    resumeText.value = r.content
    toast.success(`已加载简历「${r.name}」`)
  }
}

// ---- 用户画像 ----
const showProfile = ref(false)

function openProfile() {
  showProfile.value = true
  fetchProfile().catch(() => {})
}

async function handleSaveProfile(updates) {
  try {
    await updateProfile(updates)
    toast.success('画像已保存')
    showProfile.value = false
  } catch (e) {
    toast.error('保存画像失败：' + e.message)
  }
}

// ---- 投递看板操作 ----
const savingApp = ref(false)

async function handleUpdateStatus(appId, newStatus) {
  try {
    await updateApp(appId, { status: newStatus })
  } catch (e) {
    toast.error(e.message)
  }
}

async function handleSaveApp(payload) {
  savingApp.value = true
  try {
    const { id, ...updates } = payload
    await updateApp(id, updates)
    toast.success('已保存')
  } catch (e) {
    toast.error('保存失败：' + e.message)
  } finally {
    savingApp.value = false
  }
}

async function handleCreateApp(payload) {
  savingApp.value = true
  try {
    const { id, ...data } = payload
    await createApp(data)
    toast.success('已创建投递')
  } catch (e) {
    toast.error('创建失败：' + e.message)
  } finally {
    savingApp.value = false
  }
}

async function handleDeleteApp(appId) {
  try {
    await deleteApp(appId)
    toast.success('已删除')
  } catch (e) {
    toast.error(e.message)
  }
}

// ---- 视图切换 ----
const view = ref('chat')  // 'chat' | 'board' | 'about'

function goBoard() {
  view.value = 'board'
  fetchApps().catch(e => toast.error('加载投递记录失败：' + e.message))
}
function goChat() { view.value = 'chat' }
function goAbout() { view.value = 'about' }

function handleSwitchConversation(id) {
  switchConversation(id)
  scrollToBottom()
}
</script>

<template>
  <!-- ============================================================ -->
  <!--  登录 / 注册页面 -->
  <!-- ============================================================ -->
  <div v-if="!isLoggedIn" class="auth-page">
    <div class="auth-card">
      <h1 class="auth-logo">🤖 JobPilot</h1>
      <p class="auth-desc">AI 求职助手 — 登录或注册后开始使用</p>

      <div class="auth-tabs">
        <button :class="['tab', { active: authMode === 'login' }]" @click="authMode = 'login'">登录</button>
        <button :class="['tab', { active: authMode === 'register' }]" @click="authMode = 'register'">注册</button>
      </div>

      <form class="auth-form" @submit.prevent="handleAuth">
        <input v-model="authUser" type="text" placeholder="用户名" class="auth-input" autocomplete="username" />
        <input v-model="authPass" type="password" placeholder="密码（最少6位）" class="auth-input" autocomplete="current-password" />
        <p v-if="authError" class="auth-error">{{ authError }}</p>
        <button type="submit" class="auth-btn" :disabled="authLoading">
          {{ authLoading ? '请稍候...' : (authMode === 'register' ? '注册并登录' : '登录') }}
        </button>
      </form>
    </div>
  </div>

  <!-- ============================================================ -->
  <!--  主界面：侧边栏 + 内容区（全宽） -->
  <!-- ============================================================ -->
  <div v-else class="app-shell">
    <ConversationSidebar
      :conversations="conversations"
      :active-id="activeId"
      :username="username"
      @new="newConversation"
      @switch="handleSwitchConversation"
      @delete="deleteConversation"
      @logout="logout"
      @profile="openProfile"
    />

    <div class="main">
      <!-- 顶栏 -->
      <header class="header">
        <h1 class="logo">🤖 JobPilot</h1>
        <nav class="view-tabs">
          <button :class="['view-tab', { 'view-tab--active': view === 'chat' }]" @click="goChat">对话</button>
          <button :class="['view-tab', { 'view-tab--active': view === 'board' }]" @click="goBoard">投递看板</button>
          <button :class="['view-tab', { 'view-tab--active': view === 'about' }]" @click="goAbout">关于</button>
        </nav>
        <div class="header-right">
          <label class="mode-toggle" title="切换 Agent 版本">
            <span class="mode-label">Agent</span>
            <select
              :value="agentMode"
              @change="e => agentMode = e.target.value"
              class="mode-select"
              aria-label="切换 Agent 版本"
            >
              <option value="handwritten">手写 ReAct</option>
              <option value="langchain">LangChain</option>
            </select>
          </label>
        </div>
      </header>

      <!-- 看板视图 -->
      <div v-if="view === 'board'" class="content">
        <JobBoard
          :apps="apps"
          :loading="appsLoading"
          :saving="savingApp"
          :error="appsError"
          @refresh="fetchApps().catch(e => toast.error('刷新失败：' + e.message))"
          @update-status="handleUpdateStatus"
          @delete="handleDeleteApp"
          @save="handleSaveApp"
          @create="handleCreateApp"
        />
      </div>

      <!-- 关于视图 -->
      <div v-else-if="view === 'about'" class="content">
        <AboutView />
      </div>

      <!-- 聊天视图 -->
      <div v-else class="content chat-layout">
        <div class="chat-area" ref="chatArea">
          <div v-if="!messages.length && !loading" class="empty-state">
            <div class="empty-icon">📋</div>
            <h2>开始你的求职分析</h2>
            <p>上传简历，粘贴岗位 JD，然后告诉我你需要什么帮助</p>
            <div class="empty-hints">
              <span>你可以这样问：</span>
              <ul>
                <li>分析我的简历，指出优缺点</li>
                <li>我的简历和这个 JD 匹配吗？</li>
                <li>根据匹配结果，给我面试准备建议</li>
              </ul>
            </div>
          </div>

          <div class="messages-list">
            <ChatBubble
              v-for="(msg, i) in messages"
              :key="i"
              :message="msg"
              @save-to-board="handleSaveToBoard"
            />
            <ThinkChain :steps="thinkSteps" />
            <div v-if="error" class="err-banner">
              <span class="err-icon">⚠️</span> {{ error }}
            </div>
          </div>
        </div>

        <InputPanel
          v-model:resume-text="resumeText"
          v-model:jd-text="jdText"
          v-model:query="query"
          :loading="loading"
          :uploading="uploading"
          :file-name="fileName"
          :resumes="resumes"
          @run="handleRun"
          @upload="handleUpload"
          @stop="stopGenerating"
          @save-resume="handleSaveResume"
          @load-resume="handleLoadResume"
        />
      </div>

      <!-- 底部状态栏 -->
      <StatusBar :redis-connected="redisConnected" />
    </div>
  </div>

  <!-- 画像编辑弹窗 -->
  <ProfileModal
    v-if="showProfile"
    :profile="profile"
    :loading="profileLoading"
    @close="showProfile = false"
    @save="handleSaveProfile"
  />

  <!-- 全局 toast -->
  <ToastContainer />
</template>

<style scoped>
/* ============================================================ */
/*  登录页样式 */
/* ============================================================ */
.auth-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: #f3f4f6;
}
.auth-card {
  background: #fff;
  border-radius: 12px;
  padding: 40px 32px;
  width: 380px;
  max-width: 90vw;
  box-shadow: 0 4px 24px rgba(0,0,0,0.06);
  text-align: center;
}
.auth-logo { font-size: 28px; margin: 0 0 6px; }
.auth-desc { font-size: 13px; color: #9ca3af; margin: 0 0 20px; }
.auth-tabs { display: flex; margin-bottom: 20px; }
.tab {
  flex: 1;
  padding: 8px;
  border: none;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 14px;
  cursor: pointer;
  transition: 0.15s;
}
.tab:first-child { border-radius: 6px 0 0 6px; }
.tab:last-child { border-radius: 0 6px 6px 0; }
.tab.active { background: #2563eb; color: #fff; }
.auth-form { display: flex; flex-direction: column; gap: 12px; }
.auth-input {
  padding: 10px 14px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.15s;
}
.auth-input:focus { border-color: #2563eb; }
.auth-error { color: #dc2626; font-size: 13px; margin: 0; text-align: left; }
.auth-btn {
  padding: 10px;
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: 0.15s;
}
.auth-btn:hover { background: #1d4ed8; }
.auth-btn:disabled { opacity: 0.6; cursor: default; }

/* ============================================================ */
/*  主界面（全宽布局） */
/* ============================================================ */
.app-shell {
  display: flex;
  height: 100vh;
  width: 100%;
  font-family: system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background: #f6f7f9;
}
.main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: #f6f7f9;
}

/* 顶栏 */
.header {
  padding: 14px 24px;
  border-bottom: 1px solid #eef0f3;
  display: flex;
  align-items: center;
  gap: 20px;
  background: #fff;
  flex-shrink: 0;
}
.logo { font-size: 17px; font-weight: 700; color: #111827; margin: 0; }
.view-tabs { display: flex; gap: 4px; background: #f3f4f6; padding: 3px; border-radius: 8px; }
.view-tab {
  padding: 5px 14px;
  font-size: 13px;
  border: none;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
  border-radius: 6px;
  transition: 0.12s;
}
.view-tab:hover { background: #fff; }
.view-tab--active { background: #fff; color: #1f2937; font-weight: 600; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.header-right { margin-left: auto; display: flex; align-items: center; }
.mode-toggle { display: flex; align-items: center; gap: 6px; cursor: pointer; user-select: none; font-size: 12px; color: #6b7280; }
.mode-label { color: #9ca3af; }
.mode-select {
  font-size: 12px;
  padding: 4px 8px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  color: #4b5563;
  cursor: pointer;
  outline: none;
}
.mode-select:hover { border-color: #cbd5e1; }
.mode-select:focus { border-color: #2563eb; }

/* 内容区 */
.content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 20px 24px;
}

/* 聊天布局 */
.chat-layout {
  display: flex;
  flex-direction: column;
  padding-bottom: 0;
  overflow: hidden;
}
.chat-area { flex: 1; overflow-y: auto; padding: 24px; }
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;
  max-width: 640px;
  margin: 0 auto;
}
.empty-icon {
  width: 64px; height: 64px;
  font-size: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #eef2ff;
  border-radius: 18px;
  margin-bottom: 20px;
}
.empty-state h2 { font-size: 22px; font-weight: 700; color: #111827; margin: 0 0 8px; letter-spacing: -0.01em; }
.empty-state p { font-size: 14px; color: #6b7280; margin: 0 0 28px; }
.empty-hints {
  text-align: left;
  background: #fff;
  border: 1px solid #eef0f3;
  border-radius: 12px;
  padding: 18px 22px;
  font-size: 13px;
  color: #6b7280;
  width: 100%;
  box-shadow: 0 1px 2px rgba(16,24,40,0.03);
}
.empty-hints span { font-weight: 600; color: #374151; }
.empty-hints ul { margin: 8px 0 0; padding-left: 18px; }
.empty-hints li { margin: 5px 0; color: #6b7280; }

.messages-list { max-width: 820px; margin: 0 auto; }
.err-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  color: #dc2626;
  font-size: 13px;
  margin: 0 auto 12px;
  max-width: 820px;
}
.err-icon { font-size: 14px; }
</style>
