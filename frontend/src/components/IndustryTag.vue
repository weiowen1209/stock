<template>
  <span class="industry-tag">{{ value }}</span>
</template>

<script setup lang="ts">
defineProps<{ value: string }>()
</script>

<style scoped>
.industry-tag {
  display: inline-flex;
  padding: 5px 9px;
  border: 1px solid rgba(56, 189, 248, 0.25);
  border-radius: 10px;
  color: #7dd3fc;
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.12), rgba(15, 23, 42, 0.18));
  font-size: 12px;
  letter-spacing: 0.02em;
}
</style>
