<script setup lang="ts">
defineProps<{
  skills: string[]
}>()
</script>

<template>
  <div class="flex flex-col gap-2" role="list">
    <span class="text-body-small text-text-accent">Skills</span>
    <ul class="flex flex-wrap gap-2" aria-label="Skills list">
      <li
        v-for="skill in skills"
        :key="skill"
        class="rounded-full bg-background-2 px-3 py-1.5 text-body-small text-text-primary"
        role="listitem"
      >
        {{ skill }}
      </li>
    </ul>
  </div>
</template>
