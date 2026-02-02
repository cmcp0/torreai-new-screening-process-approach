<script setup lang="ts">
import { computed } from 'vue'
import type { CallStatus } from '../types'
import { stripBracketedMarkers } from '../utils/transcript'
import BaseButton from './ui/BaseButton.vue'

const props = defineProps<{
  status: CallStatus
  transcript?: string
}>()

const emit = defineEmits<{ 'end-call': [] }>()

const displayTranscript = computed(() =>
  props.transcript ? stripBracketedMarkers(props.transcript) : ''
)
const statusLabel = computed(() => {
  switch (props.status) {
    case 'connecting':
      return 'Connecting…'
    case 'connected':
      return 'In call'
    case 'ended':
      return 'Call ended'
    default:
      return 'Ready'
  }
})
</script>

<template>
  <div class="flex flex-col items-center gap-6" role="region" aria-label="Call">
    <p class="text-body-large text-text-primary" aria-live="polite">
      {{ statusLabel }}
    </p>
    <div v-if="displayTranscript" class="w-full max-w-md rounded bg-background-2 p-4">
      <p class="text-body-small text-text-accent">Live transcript</p>
      <p class="text-body text-text-primary">
        {{ displayTranscript === '…' ? '…' : displayTranscript }}
      </p>
    </div>
    <BaseButton
      v-if="status === 'connected'"
      variant="secondary"
      aria-label="End call"
      @click="emit('end-call')"
    >
      End call
    </BaseButton>
  </div>
</template>
