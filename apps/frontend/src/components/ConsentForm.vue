<script setup lang="ts">
import { ref } from 'vue'
import BaseButton from './ui/BaseButton.vue'

const agreed = ref(false)
const emit = defineEmits<{ accepted: [] }>()

function submit() {
  if (agreed.value) emit('accepted')
}
</script>

<template>
  <form
    class="flex max-w-lg flex-col gap-6"
    aria-label="Consent to recording and data use"
    @submit.prevent="submit"
  >
    <p class="text-body-large text-text-primary">
      By continuing, you consent to this screening call being recorded and to the use of your
      responses for evaluation purposes. Your data will be handled in accordance with our privacy
      policy.
    </p>
    <label class="flex cursor-pointer items-center gap-3">
      <input
        v-model="agreed"
        type="checkbox"
        class="h-5 w-5 rounded border-background-3 bg-background-1 text-brand focus:ring-brand"
        aria-describedby="consent-desc"
      />
      <span id="consent-desc" class="text-body text-text-primary">I agree</span>
    </label>
    <BaseButton type="submit" :disabled="!agreed" aria-label="Continue to call">
      Continue
    </BaseButton>
  </form>
</template>
