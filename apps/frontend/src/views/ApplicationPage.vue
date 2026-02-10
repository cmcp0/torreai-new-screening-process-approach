<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createApplication, ApiError } from '../api/client'
import BaseCard from '../components/ui/BaseCard.vue'
import Spinner from '../components/ui/Spinner.vue'

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const error = ref<string | null>(null)
let cancelled = false

function setError(e: unknown): string {
  if (e instanceof ApiError) return e.message
  if (e instanceof Error) return e.message
  return 'Failed to create application.'
}

onMounted(async () => {
  const username = route.query.username
  const job_offer_id = route.query.job_offer_id
  const u = typeof username === 'string' ? username.trim() : ''
  const j = typeof job_offer_id === 'string' ? job_offer_id.trim() : ''

  if (!u || !j) {
    loading.value = false
    error.value = 'Username and job offer are required.'
    return
  }

  try {
    const result = await createApplication({ username: u, job_offer_id: j })
    if (!cancelled) {
      loading.value = false
      router.replace({ path: '/call', query: { application: result.application_id } })
    }
  } catch (e) {
    if (!cancelled) {
      loading.value = false
      error.value = setError(e)
    }
  }
})

onBeforeUnmount(() => {
  cancelled = true
})
</script>

<template>
  <div class="flex min-h-screen flex-col items-center justify-center p-6">
    <BaseCard class="w-full max-w-md">
      <div v-if="loading && !error" class="flex flex-col items-center gap-4">
        <Spinner size="lg" />
        <p class="text-body text-text-accent">Creating your application…</p>
      </div>
      <div v-else-if="error" class="flex flex-col gap-4">
        <h1 class="text-h2 text-text-primary">Unable to start</h1>
        <p class="text-body text-text-primary" role="alert">{{ error }}</p>
        <a
          :href="`/application?username=${encodeURIComponent(String(route.query.username || ''))}&job_offer_id=${encodeURIComponent(String(route.query.job_offer_id || ''))}`"
          class="inline-block rounded px-4 py-2 font-button text-button text-brand underline focus:outline-none focus:ring-2 focus:ring-brand"
          aria-label="Try again"
        >
          Try again
        </a>
      </div>
    </BaseCard>
  </div>
</template>
