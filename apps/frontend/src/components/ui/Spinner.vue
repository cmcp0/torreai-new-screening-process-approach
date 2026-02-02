<script setup lang="ts">
defineProps<{
  size?: 'sm' | 'md' | 'lg'
}>()
</script>

<template>
  <div
    class="inline-block animate-spin rounded-full border-2 border-background-3 border-t-brand"
    :class="{
      'h-6 w-6': size === 'sm',
      'h-10 w-10': size === 'md' || !size,
      'h-12 w-12': size === 'lg',
    }"
    role="status"
    aria-label="Loading"
  >
    <span class="sr-only">Loading</span>
  </div>
</template>
