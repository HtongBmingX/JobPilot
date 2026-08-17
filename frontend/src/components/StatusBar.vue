<script setup>
defineProps({
  redisConnected: { type: Boolean, default: false },
})
</script>

<template>
  <div class="status-bar">
    <span class="status-item" role="status" :title="redisConnected ? 'Redis 持久化模式' : '内存模式（Redis 不可用）'">
      <span class="status-dot" :class="{ green: redisConnected, orange: !redisConnected }" aria-hidden="true"></span>
      {{ redisConnected ? 'Redis 持久化' : '内存模式' }}
    </span>
  </div>
</template>

<style scoped>
.status-bar {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 6px 24px;
  background: #f8fafc;
  border-top: 1px solid #eef0f3;
  font-size: 11px;
  color: #6b7280;
  flex-shrink: 0;
}
.status-item {
  display: flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}
.status-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  display: inline-block;
}
.status-dot.green  { background: #10b981; }
.status-dot.orange { background: #f59e0b; }
</style>
