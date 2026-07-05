<template>
  <article class="metric-card">
    <span>{{ label }}</span>
    <strong>{{ value ?? '--' }}</strong>
    <small :class="trendClass">{{ hint }}</small>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  label: string
  value?: string | number | null
  hint?: string
}>()

const trendClass = computed(() => {
  const text = props.hint ?? ''
  if (text.startsWith('-')) return 'down'
  if (text.startsWith('+')) return 'up'
  return ''
})
</script>

<style scoped>
.metric-card {
  position: relative;
  overflow: hidden;
  padding: 18px;
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 20px;
  background: linear-gradient(145deg, rgba(15, 23, 42, 0.88), rgba(8, 13, 25, 0.72));
  box-shadow: 0 20px 70px rgba(0, 0, 0, 0.24);
}

.metric-card::after {
  position: absolute;
  right: -24px;
  top: -24px;
  width: 78px;
  height: 78px;
  border-radius: 999px;
  background: rgba(45, 212, 191, 0.12);
  content: '';
}

span {
  color: #7f93ad;
  font-size: 12px;
}

strong {
  display: block;
  margin-top: 10px;
  color: #eef6ff;
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 28px;
  font-weight: 700;
}

small {
  display: block;
  margin-top: 8px;
  color: #8ba2bd;
}

.up {
  color: #f87171;
}

.down {
  color: #22c55e;
}
</style>
