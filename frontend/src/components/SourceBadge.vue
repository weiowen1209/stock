<template>
  <span class="source-badge" :class="{ stale }">
    <span class="dot"></span>
    {{ source || 'sqlite' }}
    <em v-if="updatedAt">{{ formatTime(updatedAt) }}</em>
    <strong v-if="stale">缓存</strong>
  </span>
</template>

<script setup lang="ts">
defineProps<{
  source?: string | null
  updatedAt?: string | null
  stale?: boolean
}>()

function formatTime(value: string) {
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}
</script>

<style scoped>
.source-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border: 1px solid rgba(125, 211, 252, 0.24);
  border-radius: 999px;
  color: #bde7ff;
  background: rgba(14, 23, 38, 0.72);
  font-size: 12px;
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: #2dd4bf;
  box-shadow: 0 0 14px rgba(45, 212, 191, 0.9);
}

em {
  color: #7890a9;
  font-style: normal;
}

strong {
  color: #fbbf24;
}

.stale .dot {
  background: #f59e0b;
  box-shadow: 0 0 14px rgba(245, 158, 11, 0.9);
}
</style>
