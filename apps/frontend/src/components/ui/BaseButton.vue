<script setup lang="ts">
defineProps<{
  variant?: 'primary' | 'secondary'
  disabled?: boolean
  type?: 'button' | 'submit'
}>()
</script>

<template>
  <button
    :type="type ?? 'button'"
    :disabled="disabled"
    :aria-disabled="disabled"
    class="rounded px-4 py-2 font-button text-button transition-colors focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2 focus:ring-offset-background-0 disabled:cursor-not-allowed disabled:opacity-60"
    :class="
      variant === 'secondary'
        ? 'border-2 border-background-3 bg-transparent text-text-primary hover:border-brand hover:bg-background-2'
        : 'bg-brand text-text-primary-on-accent hover:opacity-90'
    "
  >
    <slot />
  </button>
</template>
