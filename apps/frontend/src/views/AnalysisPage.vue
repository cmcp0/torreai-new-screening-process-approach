<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getAnalysis } from '../api/mock'
import type { AnalysisResult } from '../types'
import FitScoreDisplay from '../components/FitScoreDisplay.vue'
import SkillsList from '../components/SkillsList.vue'
import BaseCard from '../components/ui/BaseCard.vue'
import Skeleton from '../components/ui/Skeleton.vue'
import Spinner from '../components/ui/Spinner.vue'

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

onMounted(async () => {
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
  try {
    const id = applicationId.value
    if (typeof id !== 'string' || !id) return
    const data = await getAnalysis(id)
    result.value = data
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Analysis failed.'
  } finally {
    loading.value = false
  }
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
        <a
          href="/application"
          class="inline-block rounded px-4 py-2 font-button text-button text-brand underline focus:outline-none focus:ring-2 focus:ring-brand"
          aria-label="Back to application"
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
