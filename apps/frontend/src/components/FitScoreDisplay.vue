<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  score: number
}>()

const clampedScore = computed(() =>
  Math.min(100, Math.max(0, Number.isFinite(props.score) ? props.score : 0))
)
</script>

<template>
  <div class="flex flex-col items-center gap-2" role="region" aria-label="Fit score">
    <span class="text-display text-brand">{{ clampedScore }}%</span>
    <span class="text-body-large text-text-accent">Fit score</span>
  </div>
</template>
