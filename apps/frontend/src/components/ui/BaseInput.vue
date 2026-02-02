<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  modelValue?: string
  type?: string
  placeholder?: string
  disabled?: boolean
  label?: string
  id?: string
  error?: string
}>()

const inputId = computed(() => props.id ?? `input-${Math.random().toString(36).slice(2)}`)

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
</script>

<template>
  <div class="flex flex-col gap-1">
    <label v-if="label" :for="id ?? inputId" class="text-body-small text-text-accent">
      {{ label }}
    </label>
    <input
      :id="id ?? inputId"
      :value="modelValue"
      :type="type ?? 'text'"
      :placeholder="placeholder"
      :disabled="disabled"
      :aria-invalid="!!error"
      :aria-describedby="error ? `${inputId}-error` : undefined"
      class="rounded border-2 bg-background-1 px-3 py-2 text-body text-text-primary placeholder-text-disabled focus:border-brand focus:outline-none disabled:bg-background-2 disabled:text-text-disabled"
      :class="error ? 'border-error' : 'border-background-3'"
      @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
    />
    <p v-if="error" :id="`${inputId}-error`" class="text-body-small text-error" role="alert">
      {{ error }}
    </p>
  </div>
</template>
