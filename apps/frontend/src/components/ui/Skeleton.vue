<script setup lang="ts">
defineProps<{
  /** Optional Tailwind classes for width/height (e.g. w-48 h-4) */
  skeletonClass?: string
}>()
</script>

<template>
  <div
    class="animate-pulse rounded bg-background-2"
    :class="skeletonClass"
    role="presentation"
    aria-hidden="true"
  />
</template>
