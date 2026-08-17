<script setup>
import { computed } from 'vue'

const props = defineProps({
  conversations: { type: Array, required: true },
  activeId: { type: String, default: null },
  username: { type: String, default: '' },
})

const emit = defineEmits(['new', 'switch', 'delete', 'logout', 'profile'])

// 按更新时间倒序排列（最新的在前）
const sorted = computed(() =>
  [...props.conversations].sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0))
)

function fmtTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const now = new Date()
  const sameDay = d.toDateString() === now.toDateString()
  if (sameDay) {
    return d.toTimeString().slice(0, 5)  // HH:mm
  }
  return `${d.getMonth() + 1}/${d.getDate()}`
}
</script>

<template>
  <aside class="sidebar">
    <!-- 新建对话 -->
    <button class="new-btn" @click="emit('new')">
      <span class="new-icon">＋</span> 新建对话
    </button>

    <!-- 会话列表 -->
    <nav class="conv-list">
      <p v-if="!sorted.length" class="conv-empty">暂无对话</p>
      <div
        v-for="c in sorted"
        :key="c.id"
        class="conv-item"
        :class="{ 'conv-item--active': c.id === activeId }"
        role="button"
        :tabindex="0"
        :aria-current="c.id === activeId ? 'page' : undefined"
        @click="emit('switch', c.id)"
        @keydown.enter="emit('switch', c.id)"
        @keydown.space.prevent="emit('switch', c.id)"
      >
        <div class="conv-main">
          <span class="conv-title">{{ c.title || '未命名对话' }}</span>
          <span class="conv-time">{{ fmtTime(c.updatedAt) }}</span>
        </div>
        <button
          class="conv-del"
          title="删除对话"
          :aria-label="`删除对话：${c.title || '未命名对话'}`"
          @click.stop="emit('delete', c.id)"
        >×</button>
      </div>
    </nav>

    <!-- 底部用户区 -->
    <div class="sidebar-footer">
      <div class="user-chip">
        <span class="user-avatar">{{ (username || '?').slice(0, 1).toUpperCase() }}</span>
        <span class="user-name">{{ username || '未登录' }}</span>
      </div>
      <button class="profile-btn" @click="emit('profile')" title="编辑求职画像">画像</button>
      <button class="logout-btn" @click="emit('logout')" title="退出登录">退出</button>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 260px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: #f7f8fa;
  border-right: 1px solid #eef0f3;
  height: 100vh;
  transition: width 0.2s ease;
}

/* 移动端：侧边栏收窄为图标栏，避免挤压主区 */
@media (max-width: 768px) {
  .sidebar {
    width: 56px;
  }
  .new-btn {
    margin: 12px 8px;
    padding: 10px;
    justify-content: center;
  }
  .new-btn :deep(span:not(.new-icon)) { display: none; }
  .conv-title, .conv-time { display: none; }
  .conv-item { justify-content: center; padding: 9px 6px; }
  .conv-main { display: none; }
  .conv-del { display: none; }
  .user-name { display: none; }
  .sidebar-footer { flex-direction: column; gap: 8px; }
  .logout-btn { font-size: 11px; }
}

.new-btn {
  margin: 14px;
  padding: 10px 14px;
  border: 1px solid #dbe1ea;
  border-radius: 9px;
  background: #fff;
  color: #1f2937;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
  transition: 0.12s;
}
.new-btn:hover { border-color: #2563eb; color: #2563eb; }
.new-icon { font-size: 16px; line-height: 1; }

.conv-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 10px;
}
.conv-empty {
  font-size: 12px;
  color: #c0c7d1;
  text-align: center;
  padding: 24px 0;
}
.conv-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 9px 10px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 2px;
  transition: background 0.1s;
}
.conv-item:hover { background: #eef1f5; }
.conv-item--active { background: #e4ecfb; }
.conv-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.conv-title {
  font-size: 13px;
  color: #374151;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.conv-item--active .conv-title { color: #1d4ed8; font-weight: 500; }
.conv-time { font-size: 11px; color: #9ca3af; }
.conv-del {
  flex-shrink: 0;
  background: none;
  border: none;
  color: #c0c7d1;
  font-size: 16px;
  cursor: pointer;
  padding: 0 2px;
  opacity: 0;
  transition: opacity 0.1s;
}
.conv-item:hover .conv-del { opacity: 1; }
.conv-del:hover { color: #ef4444; }

.sidebar-footer {
  padding: 12px 14px;
  border-top: 1px solid #eef0f3;
  display: flex;
  align-items: center;
  gap: 6px;
}
.user-chip { display: flex; align-items: center; gap: 8px; min-width: 0; flex: 1; }
.user-avatar {
  width: 26px; height: 26px;
  border-radius: 50%;
  background: #2563eb;
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.user-name {
  font-size: 13px;
  color: #374151;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.profile-btn {
  background: none;
  border: none;
  color: #2563eb;
  font-size: 12px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  flex-shrink: 0;
}
.profile-btn:hover { background: #eff6ff; }
.logout-btn {
  background: none;
  border: none;
  color: #9ca3af;
  font-size: 12px;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 6px;
  flex-shrink: 0;
}
.logout-btn:hover { color: #ef4444; background: #fef2f2; }
</style>
