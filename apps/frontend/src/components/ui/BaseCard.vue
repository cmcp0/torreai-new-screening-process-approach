<script setup lang="ts">
defineProps<{
  as?: 'div' | 'section' | 'article'
}>()
</script>

<template>
  <component
    :is="as ?? 'div'"
    class="rounded-lg border border-divider bg-background-1 p-6 text-text-primary"
  >
    <slot />
  </component>
</template>
