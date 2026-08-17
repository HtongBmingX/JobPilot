<script setup>
import { computed } from 'vue'
import { parseScore, scoreTier, relativeDate } from '../utils/application.js'

const props = defineProps({
  app: { type: Object, required: true },
})

const emit = defineEmits(['update-status', 'open'])

const tier = computed(() => scoreTier(props.app.match_score))
const scoreNum = computed(() => parseScore(props.app.match_score))
const relDate = computed(() => relativeDate(props.app.applied_at))

// 匹配度百分比（用于进度条宽度）
const scorePct = computed(() => {
  const n = scoreNum.value
  if (n == null) return 0
  return Math.min(100, Math.max(0, n))
})

const summary = computed(() => {
  const text = props.app.match_summary || ''
  return text.length > 100 ? text.slice(0, 100) + '…' : text
})

function handleKeydown(e) {
  // 键盘可访问：Enter/Space 打开详情
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault()
    emit('open', props.app)
  }
}
</script>

<template>
  <div
    class="card"
    :class="'card--' + app.status"
    role="button"
    :tabindex="0"
    :aria-label="`${app.company} - ${app.position}，点击查看详情`"
    @click="emit('open', app)"
    @keydown="handleKeydown"
  >
    <!-- 顶部：公司 + 岗位 -->
    <div class="card-head">
      <div class="card-title">
        <h4 class="card-company">{{ app.company }}</h4>
        <p class="card-position">{{ app.position }}</p>
      </div>
    </div>

    <!-- 匹配度：大号数字 + 进度条（视觉锚点） -->
    <div class="card-score" :class="'score--' + tier">
      <div class="score-row">
        <span class="score-label">匹配度</span>
        <span class="score-value">
          <template v-if="scoreNum != null">{{ scoreNum }}<span class="score-unit">%</span></template>
          <template v-else>—</template>
        </span>
      </div>
      <div class="score-bar">
        <div class="score-bar-fill" :style="{ width: scorePct + '%' }"></div>
      </div>
    </div>

    <!-- 匹配摘要：关键结论 -->
    <p v-if="summary" class="card-summary">{{ summary }}</p>

    <!-- 底部：日期 + 备注 + 状态 -->
    <div class="card-footer">
      <div class="card-meta">
        <span v-if="relDate" class="card-date">{{ relDate }}</span>
        <span v-if="app.notes" class="notes-badge" title="有备注">📝 备注</span>
      </div>
      <select
        :value="app.status"
        @change="emit('update-status', app.id, $event.target.value)"
        @click.stop
        class="card-select"
        :aria-label="`切换 ${app.company} 的投递状态`"
      >
        <option value="applied">已投递</option>
        <option value="screening">初筛中</option>
        <option value="interviewing">面试中</option>
        <option value="offered">已 Offer</option>
        <option value="rejected">已拒</option>
      </select>
    </div>
  </div>
</template>

<style scoped>
.card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: #fff;
  border-radius: 12px;
  padding: 14px;
  border: 1px solid #eef0f3;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
  transition: transform 0.12s ease, box-shadow 0.12s ease, border-color 0.12s ease;
}
.card:focus-visible {
  outline: 2px solid #2563eb;
  outline-offset: 2px;
}
.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(16, 24, 40, 0.08);
  border-color: #dbe1ea;
}

/* 阶段色条：左侧 3px */
.card::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
  border-radius: 12px 0 0 12px;
}
.card--applied::before      { background: #f59e0b; }
.card--screening::before    { background: #3b82f6; }
.card--interviewing::before { background: #8b5cf6; }
.card--offered::before      { background: #10b981; }
.card--rejected::before     { background: #ef4444; }

/* 顶部：公司 + 岗位 */
.card-title { min-width: 0; }
.card-company {
  font-size: 15px;
  font-weight: 700;
  color: #111827;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  letter-spacing: -0.01em;
}
.card-position {
  font-size: 13px;
  color: #6b7280;
  margin: 2px 0 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 匹配度：大号数字 + 进度条 */
.card-score {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.score-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}
.score-label {
  font-size: 11px;
  font-weight: 500;
  color: #9ca3af;
  letter-spacing: 0.03em;
}
.score-value {
  font-size: 24px;
  font-weight: 800;
  line-height: 1;
  letter-spacing: -0.03em;
}
.score-unit { font-size: 13px; font-weight: 600; margin-left: 1px; }
.score--high .score-value { color: #059669; }
.score--mid  .score-value { color: #d97706; }
.score--low  .score-value { color: #9ca3af; }
.score--none .score-value { color: #d1d5db; }

.score-bar {
  height: 5px;
  background: #f1f3f6;
  border-radius: 3px;
  overflow: hidden;
}
.score-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}
.score--high .score-bar-fill { background: #10b981; }
.score--mid  .score-bar-fill { background: #f59e0b; }
.score--low  .score-bar-fill { background: #d1d5db; }
.score--none .score-bar-fill { background: #e5e7eb; }

/* 摘要 */
.card-summary {
  font-size: 12px;
  color: #6b7280;
  line-height: 1.55;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 底部 */
.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: auto;
  padding-top: 2px;
}
.card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: #9ca3af;
  min-width: 0;
  overflow: hidden;
}
.card-date { white-space: nowrap; }
.notes-badge {
  color: #6d28d9;
  background: #f5f3ff;
  padding: 1px 7px;
  border-radius: 5px;
  font-weight: 500;
  white-space: nowrap;
}

.card-select {
  flex-shrink: 0;
  font-size: 12px;
  padding: 4px 7px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #f9fafb;
  cursor: pointer;
  color: #4b5563;
  max-width: 110px;
}
.card-select:hover { border-color: #cbd5e1; }
.card-select:focus { outline: none; border-color: #2563eb; }
</style>
