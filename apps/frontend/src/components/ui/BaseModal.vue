<script setup lang="ts">
import { ref, watch, nextTick, onBeforeUnmount } from 'vue'

const props = defineProps<{
  open: boolean
  title?: string
}>()

const emit = defineEmits<{ close: [] }>()

const modalContentRef = ref<HTMLElement | null>(null)
let previousActiveElement: HTMLElement | null = null

const FOCUSABLE_SELECTOR =
  'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'

function getFocusables(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR))
}

function focusFirst() {
  const el = modalContentRef.value
  if (!el) return
  const focusables = getFocusables(el)
  if (focusables.length > 0) {
    previousActiveElement = document.activeElement as HTMLElement | null
    focusables[0]!.focus()
  } else {
    el.setAttribute('tabindex', '-1')
    previousActiveElement = document.activeElement as HTMLElement | null
    el.focus()
  }
}

function restoreFocus() {
  if (previousActiveElement?.focus) {
    previousActiveElement.focus()
    previousActiveElement = null
  }
}

function onKeydown(e: KeyboardEvent) {
  if (e.key !== 'Tab' || !modalContentRef.value) return
  const focusables = getFocusables(modalContentRef.value)
  if (focusables.length === 0) return
  const current = document.activeElement as HTMLElement | null
  const currentIndex = current ? focusables.indexOf(current) : -1
  if (e.shiftKey) {
    if (currentIndex <= 0) {
      e.preventDefault()
      focusables[focusables.length - 1]!.focus()
    }
  } else {
    if (currentIndex === -1 || currentIndex >= focusables.length - 1) {
      e.preventDefault()
      focusables[0]!.focus()
    }
  }
}

watch(
  () => props.open,
  (open) => {
    if (open) {
      nextTick(() => focusFirst())
    } else {
      restoreFocus()
    }
  }
)

onBeforeUnmount(() => {
  restoreFocus()
})

function onBackdropClick(e: MouseEvent) {
  if ((e.target as HTMLElement).getAttribute('data-modal-backdrop') === 'true') {
    emit('close')
  }
}
</script>

<template>
  <Teleport to="body">
    <div
      v-show="open"
      data-modal-backdrop="true"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="title ? 'modal-title' : undefined"
      @click="onBackdropClick"
      @keydown="onKeydown"
    >
      <div
        ref="modalContentRef"
        class="max-w-md rounded-lg border border-divider bg-background-1 p-6 shadow-xl focus:outline-none"
        role="document"
        @click.stop
      >
        <h2 v-if="title" id="modal-title" class="text-h3 mb-4 text-text-primary">
          {{ title }}
        </h2>
        <slot />
      </div>
    </div>
  </Teleport>
</template>
