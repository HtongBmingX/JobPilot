<script setup>
import { computed, ref } from 'vue'
import { renderMarkdown } from '../utils/markdown.js'

const props = defineProps({
  message: { type: Object, required: true },
})

const emit = defineEmits(['save-to-board'])

const isUser = computed(() => props.message.role === 'user')
const displayContent = computed(() => {
  if (props.message.isMarkdown && !isUser.value) {
    return renderMarkdown(props.message.content || '')
  }
  return props.message.content || ''
})

// 复制原文
const copied = ref(false)
async function handleCopy() {
  try {
    await navigator.clipboard.writeText(props.message.content || '')
    copied.value = true
    setTimeout(() => { copied.value = false }, 1500)
  } catch {
    /* 剪贴板不可用时静默失败 */
  }
}

// 宽松提取——只要消息够长且包含分析类关键词就显示保存按钮
const shouldShowSave = computed(() => {
  const text = props.message.content || ''
  if (isUser.value || text.length < 80) return false
  return /匹配|分析|评估|适合|推荐|建议|契合|胜任|优缺点|改进|表现|技能|经验/i.test(text)
})

const saving = ref(false)
const showManual = ref(false)
const manual = ref({ company: '', position: '', score: '' })

function tryExtract() {
  const text = props.message.content || ''
  let company = ''
  let position = ''
  let score = ''

  const companyM = text.match(/(?:公司|企业)[名称]*[:：]\s*(.+?)(?:\n|$|，|。|<)/)
  if (companyM) company = companyM[1].trim()

  const positionM = text.match(/(?:岗位|职位)[名称]*[:：]\s*(.+?)(?:\n|$|，|。|<)/)
  if (positionM) position = positionM[1].trim()

  const scoreM = text.match(/(?:匹配度|匹配分数|综合评分|契合度)[:：]*\s*(\d+\s*%|\d+\s*分|[\d.]+\s*\/\s*100)/i)
  if (scoreM) {
    score = scoreM[1].replace(/\s/g, '')
    if (score.includes('/100')) score = score.split('/')[0] + '%'
    if (!score.includes('%') && !score.includes('分')) score += '%'
  }

  if (!company) {
    showManual.value = true
    return { company: '', position, score }
  }
  return { company, position, score }
}

async function handleSave() {
  const extracted = tryExtract()
  // 提取不到公司名时，展示手动输入框，等用户填写后点"确认"再保存
  if (!extracted.company && !manual.value.company) {
    showManual.value = true
    return
  }
  saving.value = true
  try {
    emit('save-to-board', {
      company: extracted.company || manual.value.company || '待填写',
      position: extracted.position || manual.value.position || '待填写',
      match_score: extracted.score || manual.value.score || '',
      match_summary: props.message.content.slice(0, 200),
      applied_at: new Date().toISOString().slice(0, 10),
    })
    showManual.value = false
    manual.value = { company: '', position: '', score: '' }
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="bubble" :class="isUser ? 'user' : 'assistant'">
    <div class="bubble-avatar">{{ isUser ? '👤' : '🤖' }}</div>
    <div class="bubble-content">
      <div class="bubble-role">{{ isUser ? '你' : 'JobPilot' }}</div>

      <div v-if="isUser" class="bubble-text">{{ message.content }}</div>
      <div v-else class="bubble-text markdown-body" v-html="displayContent"></div>

      <!-- 操作区：复制 + 保存看板（AI 消息 hover 显示） -->
      <div v-if="!isUser && message.content" class="bubble-actions">
        <button class="bubble-action" @click="handleCopy">
          {{ copied ? '✓ 已复制' : '复制' }}
        </button>
        <button v-if="shouldShowSave" class="bubble-action bubble-action--primary" @click="handleSave" :disabled="saving">
          {{ saving ? '保存中…' : '📌 保存到看板' }}
        </button>
      </div>

      <!-- 手动输入兜底 -->
      <div v-if="showManual" class="save-manual">
        <input v-model="manual.company" placeholder="公司名" class="save-input" />
        <input v-model="manual.position" placeholder="岗位" class="save-input" />
        <input v-model="manual.score" placeholder="匹配度" class="save-input save-input--short" />
        <button class="save-confirm" @click="handleSave">确认</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.bubble {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}
.bubble.user { flex-direction: row-reverse; }
.bubble-avatar {
  width: 34px; height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
  margin-top: 2px;
}
.bubble.user .bubble-avatar { background: #2563eb; }
.bubble.assistant .bubble-avatar { background: #eef2ff; border: 1px solid #e0e7ff; }

.bubble-content { max-width: 78%; min-width: 0; }
.bubble-role { font-size: 11px; color: #9ca3af; margin-bottom: 4px; }
.bubble.user .bubble-role { text-align: right; }

.bubble-text {
  padding: 12px 16px;
  border-radius: 14px;
  font-size: 14px;
  line-height: 1.7;
  color: #1f2937;
  word-break: break-word;
}
.bubble.user .bubble-text {
  background: #2563eb;
  color: #fff;
  border-bottom-right-radius: 4px;
}
.bubble.assistant .bubble-text {
  background: #fff;
  border: 1px solid #eef0f3;
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 2px rgba(16,24,40,0.03);
}

/* Markdown 排版 */
.markdown-body :deep(h2) { font-size: 16px; font-weight: 700; margin: 18px 0 8px; padding-bottom: 6px; border-bottom: 1px solid #f1f3f6; color: #111827; }
.markdown-body :deep(h2:first-child) { margin-top: 0; }
.markdown-body :deep(h3) { font-size: 14px; font-weight: 600; margin: 14px 0 6px; color: #374151; }
.markdown-body :deep(p) { margin: 8px 0; line-height: 1.75; color: #4b5563; }
.markdown-body :deep(ul), .markdown-body :deep(ol) { margin: 8px 0; padding-left: 22px; color: #4b5563; }
.markdown-body :deep(li) { margin: 3px 0; line-height: 1.65; }
.markdown-body :deep(strong) { color: #111827; font-weight: 700; }
.markdown-body :deep(code) { background: #f3f4f6; padding: 2px 6px; border-radius: 4px; font-size: 13px; color: #be185d; font-family: ui-monospace, 'SF Mono', monospace; }
.markdown-body :deep(pre) { background: #1f2937; color: #f9fafb; padding: 14px; border-radius: 8px; overflow-x: auto; font-size: 13px; line-height: 1.5; margin: 8px 0; }
.markdown-body :deep(pre code) { background: none; padding: 0; color: inherit; }
.markdown-body :deep(table) { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 13px; }
.markdown-body :deep(th) { background: #f9fafb; padding: 8px 10px; text-align: left; font-weight: 600; border: 1px solid #e5e7eb; color: #374151; }
.markdown-body :deep(td) { padding: 8px 10px; border: 1px solid #eef0f3; }
.markdown-body :deep(blockquote) { border-left: 3px solid #2563eb; margin: 10px 0; padding: 6px 14px; background: #f8faff; color: #6b7280; border-radius: 0 6px 6px 0; }
.markdown-body :deep(hr) { border: none; border-top: 1px solid #eef0f3; margin: 14px 0; }

/* 操作区 */
.bubble-actions {
  margin-top: 6px;
  display: flex;
  gap: 6px;
  opacity: 0;
  transition: opacity 0.12s;
}
.bubble:hover .bubble-actions { opacity: 1; }
.bubble-action {
  padding: 4px 10px;
  font-size: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #fff;
  color: #6b7280;
  cursor: pointer;
  transition: 0.12s;
}
.bubble-action:hover { color: #2563eb; border-color: #bfdbfe; background: #eff6ff; }
.bubble-action--primary { color: #2563eb; }
.bubble-action:disabled { opacity: 0.5; cursor: default; }

.save-manual {
  margin-top: 8px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.save-input {
  flex: 1;
  min-width: 100px;
  padding: 5px 8px;
  font-size: 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
}
.save-input--short { flex: 0 0 80px; }
.save-confirm {
  padding: 5px 12px;
  font-size: 12px;
  border: none;
  border-radius: 6px;
  background: #2563eb;
  color: #fff;
  cursor: pointer;
}
.save-confirm:hover { background: #1d4ed8; }
</style>
