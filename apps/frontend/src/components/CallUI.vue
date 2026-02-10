<script setup lang="ts">
import { computed } from 'vue'
import type { CallStatus, CallSubstatus } from '../types'
import { stripBracketedMarkers } from '../utils/transcript'
import BaseButton from './ui/BaseButton.vue'

type TranscriptSpeaker = 'emma' | 'candidate' | 'system'

type TranscriptMessage = {
  speaker: TranscriptSpeaker
  text: string
}

const props = defineProps<{
  status: CallStatus
  substatus?: CallSubstatus
  transcript?: string
  emmaSpeaking?: boolean
}>()

const emit = defineEmits<{ 'end-call': [] }>()

const transcriptMessages = computed<TranscriptMessage[]>(() => {
  if (!props.transcript?.trim()) return []

  return props.transcript
    .split(/\n{2,}/)
    .map((chunk) => chunk.trim())
    .filter(Boolean)
    .map((chunk) => {
      const candidateMatch = chunk.match(/^you:\s*/i)
      const emmaMatch = chunk.match(/^emma:\s*/i)

      let speaker: TranscriptSpeaker = 'system'
      let rawText = chunk

      if (candidateMatch) {
        speaker = 'candidate'
        rawText = chunk.slice(candidateMatch[0].length).trim()
      } else if (emmaMatch) {
        speaker = 'emma'
        rawText = chunk.slice(emmaMatch[0].length).trim()
      }

      const text = stripBracketedMarkers(rawText)
      if (!text) return null
      return { speaker, text }
    })
    .filter((msg): msg is TranscriptMessage => !!msg)
})
const statusLabel = computed(() => {
  switch (props.status) {
    case 'connecting':
      return 'Connecting…'
    case 'connected':
      if (props.emmaSpeaking || props.substatus === 'emma_speaking') return 'Emma is speaking…'
      if (props.substatus === 'listening') return 'Your turn — speak now'
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
    <div v-if="transcriptMessages.length" class="w-full max-w-md">
      <p class="text-body-small text-text-accent">Live transcript</p>
      <div class="mt-3 max-h-72 space-y-3 overflow-y-auto rounded-lg border border-divider bg-background-0/40 p-3">
        <div
          v-for="(message, index) in transcriptMessages"
          :key="`${message.speaker}-${index}`"
          class="flex"
          :class="{
            'justify-start': message.speaker !== 'candidate',
            'justify-end': message.speaker === 'candidate',
          }"
        >
          <article
            class="max-w-[85%] rounded-2xl px-4 py-3"
            :class="{
              'bg-background-2 text-text-primary': message.speaker === 'emma',
              'border border-brand bg-brand/20 text-text-primary': message.speaker === 'candidate',
              'bg-background-1 text-text-accent': message.speaker === 'system',
            }"
          >
            <p class="mb-1 text-caption font-semibold uppercase tracking-wide text-text-accent">
              {{
                message.speaker === 'candidate'
                  ? 'You'
                  : message.speaker === 'emma'
                    ? 'Emma'
                    : 'Call'
              }}
            </p>
            <p class="text-body whitespace-pre-line">
              {{ message.text }}
            </p>
          </article>
        </div>
      </div>
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
