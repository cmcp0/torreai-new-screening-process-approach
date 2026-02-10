<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { getAnalysis, ApiError } from '../api/client'
import type { AnalysisResult } from '../types'
import FitScoreDisplay from '../components/FitScoreDisplay.vue'
import SkillsList from '../components/SkillsList.vue'
import BaseCard from '../components/ui/BaseCard.vue'
import Skeleton from '../components/ui/Skeleton.vue'
import Spinner from '../components/ui/Spinner.vue'

const POLL_INTERVAL_MS = 2500
const POLL_MAX_DURATION_MS = 5 * 60 * 1000
const POLL_MAX_ATTEMPTS = 100

const route = useRoute()
const applicationId = computed(() => {
  const a = route.query.application_id
  if (typeof a === 'string') return a.trim()
  if (Array.isArray(a) || (a != null && typeof a !== 'string')) return null
  return ''
})
const hasApplicationId = computed(() => typeof applicationId.value === 'string' && applicationId.value.length > 0)
const paramError = computed<'missing' | 'invalid' | null>(() => {
  const a = route.query.application_id
  if (Array.isArray(a) || (a != null && typeof a !== 'string')) return 'invalid'
  if (typeof a === 'string' && a.trim() === '') return 'missing'
  if (a == null || a === '') return 'missing'
  return null
})

const loading = ref(true)
const error = ref<string | null>(null)
const result = ref<AnalysisResult | null>(null)
const pollTimedOut = ref(false)
const canRetry = ref(false)
let pollTimer: ReturnType<typeof setTimeout> | null = null

function clearPollTimer() {
  if (pollTimer != null) {
    clearTimeout(pollTimer)
    pollTimer = null
  }
}

async function fetchOnce() {
  const id = applicationId.value
  if (typeof id !== 'string' || !id) return
  const data = await getAnalysis(id)
  result.value = data
  loading.value = false
  clearPollTimer()
}

function schedulePoll(startTime: number, attempt: number) {
  if (attempt >= POLL_MAX_ATTEMPTS || Date.now() - startTime >= POLL_MAX_DURATION_MS) {
    loading.value = false
    pollTimedOut.value = true
    canRetry.value = true
    error.value = 'Analysis is taking longer than expected. Please check back later.'
    return
  }
  pollTimer = setTimeout(() => {
    pollTimer = null
    doPoll(startTime, attempt + 1)
  }, POLL_INTERVAL_MS)
}

async function doPoll(startTime: number, attempt: number) {
  const id = applicationId.value
  if (typeof id !== 'string' || !id) return
  try {
    const data = await getAnalysis(id)
    result.value = data
    loading.value = false
    clearPollTimer()
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.status === 202) {
        schedulePoll(startTime, attempt)
        return
      }
      if (e.status === 404) {
        loading.value = false
        error.value = 'Application not found'
        clearPollTimer()
        return
      }
    }
    loading.value = false
    error.value = e instanceof ApiError ? e.message : 'Analysis failed.'
    clearPollTimer()
  }
}

async function startFetch() {
  const id = applicationId.value
  if (typeof id !== 'string' || !id) return
  const startTime = Date.now()
  try {
    const data = await getAnalysis(id)
    result.value = data
  } catch (e) {
    if (e instanceof ApiError && e.status === 202) {
      schedulePoll(startTime, 1)
      return
    }
    if (e instanceof ApiError && e.status === 404) {
      error.value = 'Application not found'
      canRetry.value = false
    } else {
      error.value = e instanceof ApiError ? e.message : 'Analysis failed.'
      canRetry.value = true
    }
  } finally {
    if (result.value != null || error.value != null || pollTimedOut.value) {
      loading.value = false
    }
  }
}

function retry() {
  error.value = null
  pollTimedOut.value = false
  canRetry.value = false
  loading.value = true
  startFetch()
}

onMounted(() => {
  if (paramError.value === 'invalid') {
    loading.value = false
    error.value = 'Invalid application ID.'
    return
  }
  if (!hasApplicationId.value) {
    loading.value = false
    error.value = 'Application ID is required.'
    return
  }
  startFetch()
})

onBeforeUnmount(() => {
  clearPollTimer()
})
</script>

<template>
  <div class="flex min-h-screen flex-col items-center justify-center p-6">
    <BaseCard class="w-full max-w-md">
      <template v-if="paramError">
        <h1 class="text-h2 mb-4 text-text-primary">
          {{ paramError === 'invalid' ? 'Invalid application' : 'Missing application' }}
        </h1>
        <p class="mb-4 text-body text-text-primary">
          {{ paramError === 'invalid' ? 'Invalid application ID.' : 'This page requires an application ID. Please complete a call first.' }}
        </p>
        <a
          href="/application"
          class="inline-block rounded px-4 py-2 font-button text-button text-brand underline focus:outline-none focus:ring-2 focus:ring-brand"
          aria-label="Go to application"
        >
          Go to application
        </a>
      </template>
      <template v-else-if="loading">
        <div class="flex flex-col gap-4">
          <div class="flex flex-col items-center gap-2">
            <Skeleton skeleton-class="h-12 w-24" />
            <Skeleton skeleton-class="h-4 w-48" />
          </div>
          <div class="flex flex-col items-center gap-4">
            <Spinner size="lg" />
            <p class="text-body text-text-accent">Analyzing your call…</p>
          </div>
        </div>
      </template>
      <template v-else-if="error">
        <h1 class="text-h2 mb-4 text-text-primary">Analysis failed</h1>
        <p class="mb-4 text-body text-text-primary" role="alert">{{ error }}</p>
        <div class="flex flex-wrap gap-3">
          <a
            href="/application"
            class="inline-block rounded px-4 py-2 font-button text-button text-brand underline focus:outline-none focus:ring-2 focus:ring-brand"
            aria-label="Go to application"
          >
            Go to application
          </a>
          <button
            v-if="canRetry"
            type="button"
            class="rounded bg-brand px-4 py-2 font-button text-button text-white focus:outline-none focus:ring-2 focus:ring-brand"
            aria-label="Retry"
            @click="retry"
          >
            Retry
          </button>
        </div>
      </template>
      <template v-else-if="result?.failed">
        <h1 class="text-h2 mb-4 text-text-primary">Analysis unavailable</h1>
        <p class="mb-4 text-body text-text-primary" role="alert">
          We couldn't complete the analysis for this call. Please try again later or start a new application.
        </p>
        <a
          href="/application"
          class="inline-block rounded px-4 py-2 font-button text-button text-brand underline focus:outline-none focus:ring-2 focus:ring-brand"
          aria-label="Go to application"
        >
          Go to application
        </a>
      </template>
      <template v-else-if="result">
        <h1 class="text-h2 mb-6 text-text-primary">Your results</h1>
        <div class="flex flex-col gap-8">
          <FitScoreDisplay :score="result.fit_score" />
          <SkillsList :skills="result.skills" />
        </div>
      </template>
    </BaseCard>
  </div>
</template>
