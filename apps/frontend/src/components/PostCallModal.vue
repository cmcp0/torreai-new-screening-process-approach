<script setup lang="ts">
import { useRouter } from 'vue-router'
import BaseButton from './ui/BaseButton.vue'
import BaseModal from './ui/BaseModal.vue'

const props = defineProps<{
  open: boolean
  applicationId: string
}>()

const router = useRouter()

/** Single-action modal: only "View analysis" navigates; backdrop does not close (spec). */
function goToAnalysis() {
  router.push({ path: '/analysis', query: { application_id: props.applicationId } })
}
</script>

<template>
  <BaseModal :open="open" title="Call ended" @close="() => {}">
    <p class="mb-6 text-body text-text-primary">
      Your screening call has ended. You can view your analysis results below.
    </p>
    <BaseButton aria-label="View analysis" @click="goToAnalysis">
      View analysis
    </BaseButton>
  </BaseModal>
</template>
