<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import type { CallStatus } from '../types'
import ConsentForm from '../components/ConsentForm.vue'
import CallUI from '../components/CallUI.vue'
import PostCallModal from '../components/PostCallModal.vue'
import BaseCard from '../components/ui/BaseCard.vue'

const route = useRoute()
const applicationId = computed(() => {
  const a = route.query.application
  return typeof a === 'string' ? a.trim() : ''
})
const hasApplication = computed(() => !!applicationId.value)

const consentAccepted = ref(false)
const callStatus = ref<CallStatus>('idle')
const showPostCallModal = ref(false)
const transcript = ref('')

function onConsentAccepted() {
  consentAccepted.value = true
  callStatus.value = 'connecting'
  setTimeout(() => {
    callStatus.value = 'connected'
    transcript.value = 'Hello, welcome to the screening. [typing] How are you today?'
  }, 800)
}

function onEndCall() {
  callStatus.value = 'ended'
  showPostCallModal.value = true
}
</script>

<template>
  <div class="flex min-h-screen flex-col items-center justify-center p-6">
    <template v-if="!hasApplication">
      <BaseCard class="w-full max-w-md">
        <h1 class="text-h2 mb-4 text-text-primary">Missing application</h1>
        <p class="mb-4 text-body text-text-primary">
          This page requires an application ID. Please start from the application page.
        </p>
        <a
          href="/application"
          class="inline-block rounded px-4 py-2 font-button text-button text-brand underline focus:outline-none focus:ring-2 focus:ring-brand"
          aria-label="Go to application"
        >
          Go to application
        </a>
      </BaseCard>
    </template>
    <template v-else>
      <BaseCard v-if="!consentAccepted" class="w-full max-w-lg">
        <h1 class="text-h2 mb-6 text-text-primary">Consent</h1>
        <ConsentForm @accepted="onConsentAccepted" />
      </BaseCard>
      <BaseCard v-else class="w-full max-w-lg">
        <h1 class="text-h2 mb-6 text-text-primary">Screening call</h1>
        <CallUI
          :status="callStatus"
          :transcript="transcript"
          @end-call="onEndCall"
        />
      </BaseCard>
      <PostCallModal
        :open="showPostCallModal"
        :application-id="applicationId"
      />
    </template>
  </div>
</template>
