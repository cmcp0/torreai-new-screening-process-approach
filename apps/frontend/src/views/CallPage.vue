<script setup lang="ts">
import { ref, computed, onBeforeUnmount, watch } from 'vue'
import { useRoute } from 'vue-router'
import type { CallStatus, CallSubstatus } from '../types'
import { wsCallUrl } from '../api/config'
import ConsentForm from '../components/ConsentForm.vue'
import CallUI from '../components/CallUI.vue'
import PostCallModal from '../components/PostCallModal.vue'
import BaseCard from '../components/ui/BaseCard.vue'

type SpeechRecognitionCtor = new () => any

type ClientTextMessage = { type: 'text'; text: string }
type ClientAudioStartMessage = { type: 'audio_start'; codec?: string; sample_rate_hz?: number }
type ClientAudioChunkMessage = { type: 'audio_chunk'; data_b64: string; seq: number; is_final: boolean }
type ClientAudioEndMessage = { type: 'audio_end' }
type ServerControlMessage = { type: 'control'; event: 'emma_speaking' | 'listening' | 'call_ended' }
type ServerTextMessage = { type: 'text'; text: string; speaker?: string }
type ServerAudioChunkMessage = {
  type: 'audio_chunk'
  speaker: 'emma' | 'candidate'
  is_final?: boolean
}

const SpeechRecognitionAPI =
  typeof window !== 'undefined' &&
  ((window as unknown as { SpeechRecognition?: SpeechRecognitionCtor }).SpeechRecognition
    || (window as unknown as { webkitSpeechRecognition?: SpeechRecognitionCtor }).webkitSpeechRecognition)
const DUPLICATE_CALL_CLOSE_CODE = 4409
const AUDIO_CHUNK_SLICE_MS = 300
const AUDIO_MAX_TURN_DURATION_MS = 45000
const AUDIO_FALLBACK_TURN_DURATION_MS = 12000
const AUDIO_SILENCE_CHECK_INTERVAL_MS = 120
const AUDIO_SILENCE_HANGOVER_MS = 1400
const AUDIO_SILENCE_RMS_THRESHOLD = 0.012
const SPEECH_RESULT_DEBOUNCE_MS = 1800
const WS_AUDIO_STREAMING_MODE = String(import.meta.env.VITE_WS_AUDIO_STREAMING || 'false').toLowerCase()
const WS_AUDIO_STREAMING_FORCE = WS_AUDIO_STREAMING_MODE === 'force'
const WS_AUDIO_STREAMING_ENABLED = WS_AUDIO_STREAMING_FORCE
const AUDIO_MIME_TYPE = 'audio/webm;codecs=opus'

const route = useRoute()
const applicationId = computed(() => {
  const a = route.query.application
  return typeof a === 'string' ? a.trim() : ''
})
const hasApplication = computed(() => !!applicationId.value)

const consentAccepted = ref(false)
const callStatus = ref<CallStatus>('idle')
const callSubstatus = ref<CallSubstatus>(null)
const showPostCallModal = ref(false)
const wsError = ref<string | null>(null)
const transcript = ref('')
const speechRecognitionDisabled = ref(!SpeechRecognitionAPI)
const microphoneGranted = ref(false)
const awaitingBackendTurn = ref(false)
const emmaAudioSpeaking = ref(false)
const audioStreamingEnabled = ref(WS_AUDIO_STREAMING_ENABLED)

let ws: WebSocket | null = null
let recognition: any | null = null
let pendingRestartTimer: number | null = null
let preferredEmmaVoice: SpeechSynthesisVoice | null = null
let mediaRecorder: MediaRecorder | null = null
let mediaStream: MediaStream | null = null
let audioTurnTimer: number | null = null
let audioSilenceTimer: number | null = null
let audioContext: AudioContext | null = null
let audioAnalyser: AnalyserNode | null = null
let audioStreamSource: MediaStreamAudioSourceNode | null = null
let hasDetectedCandidateSpeech = false
let lastDetectedSpeechAt = 0
let pendingSpeechDebounceTimer: number | null = null
let pendingSpeechTranscript = ''
let nextAudioSeq = 0
let sentAudioEnd = false

const canUseMediaRecorder = computed(() =>
  typeof window !== 'undefined' && typeof window.MediaRecorder !== 'undefined'
)

const shouldUseAudioStreaming = computed(() =>
  audioStreamingEnabled.value
  && canUseMediaRecorder.value
  && microphoneGranted.value
  && WS_AUDIO_STREAMING_FORCE
)

const canCaptureCandidateTurn = computed(() =>
  callStatus.value === 'connected'
  && callSubstatus.value === 'listening'
  && !awaitingBackendTurn.value
  && !emmaAudioSpeaking.value
)

function getMediaSampleRate(stream: MediaStream): number {
  const tracks = stream.getAudioTracks()
  if (!tracks.length) return 16000
  const firstTrack = tracks[0]
  if (!firstTrack) return 16000
  const settings = firstTrack.getSettings()
  return typeof settings.sampleRate === 'number' ? settings.sampleRate : 16000
}

function sendWsMessage(
  message: ClientTextMessage | ClientAudioStartMessage | ClientAudioChunkMessage | ClientAudioEndMessage
): void {
  if (ws?.readyState !== WebSocket.OPEN) return
  ws.send(JSON.stringify(message))
}

async function requestMicrophonePermission(): Promise<{ granted: boolean; reason?: string }> {
  if (typeof window !== 'undefined' && window.isSecureContext === false) {
    return { granted: false, reason: 'Microphone access requires HTTPS (or localhost).' }
  }
  if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
    return { granted: false, reason: 'This browser does not support microphone capture for this page.' }
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    stream.getTracks().forEach((track) => track.stop())
    return { granted: true }
  } catch (error: any) {
    const message = typeof error?.message === 'string' && error.message.trim()
      ? error.message.trim()
      : 'Permission denied or unavailable.'
    return { granted: false, reason: `Microphone permission is required. ${message}` }
  }
}

function speak(text: string) {
  if (typeof window === 'undefined' || !window.speechSynthesis) return
  window.speechSynthesis.cancel()
  const u = new SpeechSynthesisUtterance(text)
  u.rate = 0.95
  emmaAudioSpeaking.value = true
  u.onstart = () => {
    emmaAudioSpeaking.value = true
  }
  const markSpeechEnded = () => {
    emmaAudioSpeaking.value = false
    triggerCandidateCaptureIfReady()
  }
  u.onend = markSpeechEnded
  u.onerror = markSpeechEnded
  if (!preferredEmmaVoice) preferredEmmaVoice = getPreferredEmmaVoice()
  if (preferredEmmaVoice) u.voice = preferredEmmaVoice
  window.speechSynthesis.speak(u)
}

function getPreferredEmmaVoice(): SpeechSynthesisVoice | null {
  if (typeof window === 'undefined' || !window.speechSynthesis) return null
  const voices = window.speechSynthesis.getVoices()
  if (!voices.length) return null

  const femaleHints = [
    'female',
    'woman',
    'samantha',
    'victoria',
    'karen',
    'moira',
    'zira',
    'ava',
    'allison',
    'serena',
    'aria',
  ]

  const englishVoices = voices.filter((v) => v.lang?.toLowerCase().startsWith('en'))
  const candidates = englishVoices.length ? englishVoices : voices
  const hinted = candidates.find((v) =>
    femaleHints.some((h) => v.name.toLowerCase().includes(h))
  )
  return hinted || candidates[0] || null
}

function sendCandidateText(text: string) {
  const t = text?.trim()
  if (!t) return
  if (ws?.readyState !== WebSocket.OPEN) return
  awaitingBackendTurn.value = true
  sendWsMessage({ type: 'text', text: t })
}

function appendTranscriptLine(text: string, speaker?: string) {
  const t = text?.trim()
  if (!t) return
  const prefix = speaker === 'candidate' ? 'You: ' : speaker === 'emma' ? 'Emma: ' : ''
  transcript.value = (transcript.value ? `${transcript.value}\n\n` : '') + `${prefix}${t}`
}

async function blobToBase64(blob: Blob): Promise<string> {
  const buf = await blob.arrayBuffer()
  let binary = ''
  const bytes = new Uint8Array(buf)
  bytes.forEach((b) => {
    binary += String.fromCharCode(b)
  })
  return btoa(binary)
}

function clearAudioTurnTimer() {
  if (audioTurnTimer) {
    window.clearTimeout(audioTurnTimer)
    audioTurnTimer = null
  }
}

function clearAudioSilenceTimer() {
  if (audioSilenceTimer) {
    window.clearInterval(audioSilenceTimer)
    audioSilenceTimer = null
  }
}

function clearPendingSpeechDebounceTimer() {
  if (pendingSpeechDebounceTimer) {
    window.clearTimeout(pendingSpeechDebounceTimer)
    pendingSpeechDebounceTimer = null
  }
}

function clearSpeechCaptureBuffer() {
  pendingSpeechTranscript = ''
  clearPendingSpeechDebounceTimer()
}

function computeRms(buffer: Float32Array): number {
  if (!buffer.length) return 0
  let sum = 0
  for (let idx = 0; idx < buffer.length; idx += 1) {
    const sample = buffer[idx] || 0
    sum += sample * sample
  }
  return Math.sqrt(sum / buffer.length)
}

function stopAudioSilenceDetection() {
  clearAudioSilenceTimer()

  if (audioStreamSource) {
    try {
      audioStreamSource.disconnect()
    } catch {
      /* ignore */
    }
    audioStreamSource = null
  }

  if (audioAnalyser) {
    try {
      audioAnalyser.disconnect()
    } catch {
      /* ignore */
    }
    audioAnalyser = null
  }

  if (audioContext) {
    const ctx = audioContext
    audioContext = null
    void ctx.close().catch(() => undefined)
  }

  hasDetectedCandidateSpeech = false
  lastDetectedSpeechAt = 0
}

function startAudioSilenceDetection(stream: MediaStream): boolean {
  stopAudioSilenceDetection()
  if (typeof window === 'undefined') return false

  const audioWindow = window as Window & typeof globalThis & { webkitAudioContext?: typeof AudioContext }
  const AudioContextCtor = audioWindow.AudioContext || audioWindow.webkitAudioContext
  if (!AudioContextCtor) return false

  try {
    audioContext = new AudioContextCtor()
    audioAnalyser = audioContext.createAnalyser()
    audioAnalyser.fftSize = 1024
    audioAnalyser.smoothingTimeConstant = 0.2
    audioStreamSource = audioContext.createMediaStreamSource(stream)
    audioStreamSource.connect(audioAnalyser)

    hasDetectedCandidateSpeech = false
    lastDetectedSpeechAt = Date.now()
    const samples = new Float32Array(audioAnalyser.fftSize)

    audioSilenceTimer = window.setInterval(() => {
      if (!audioAnalyser || !mediaRecorder || mediaRecorder.state !== 'recording') return

      audioAnalyser.getFloatTimeDomainData(samples)
      const rms = computeRms(samples)
      const now = Date.now()

      if (rms >= AUDIO_SILENCE_RMS_THRESHOLD) {
        hasDetectedCandidateSpeech = true
        lastDetectedSpeechAt = now
        return
      }

      if (
        hasDetectedCandidateSpeech
        && (now - lastDetectedSpeechAt) >= AUDIO_SILENCE_HANGOVER_MS
      ) {
        stopAudioCapture({ sendEnd: true, awaitBackend: true })
      }
    }, AUDIO_SILENCE_CHECK_INTERVAL_MS)

    return true
  } catch {
    stopAudioSilenceDetection()
    return false
  }
}

function extractSpeechTranscript(event: any): string {
  const parts: string[] = []
  const results = event?.results
  if (!results?.length) return ''

  for (let idx = 0; idx < results.length; idx += 1) {
    const text = results[idx]?.[0]?.transcript?.trim()
    if (text) parts.push(text)
  }

  return parts.join(' ').replace(/\s+/g, ' ').trim()
}

function releaseMediaStream() {
  stopAudioSilenceDetection()
  if (!mediaStream) return
  mediaStream.getTracks().forEach((t) => t.stop())
  mediaStream = null
}

function stopAudioCapture(options: { sendEnd: boolean; awaitBackend: boolean }) {
  clearAudioTurnTimer()
  stopAudioSilenceDetection()

  if (!mediaRecorder) {
    if (options.sendEnd && !sentAudioEnd && ws?.readyState === WebSocket.OPEN) {
      sendWsMessage({ type: 'audio_end' })
      sentAudioEnd = true
      if (options.awaitBackend) awaitingBackendTurn.value = true
    }
    return
  }

  if (options.sendEnd && !sentAudioEnd && ws?.readyState === WebSocket.OPEN) {
    sendWsMessage({ type: 'audio_end' })
    sentAudioEnd = true
    if (options.awaitBackend) awaitingBackendTurn.value = true
  }

  try {
    mediaRecorder.stop()
  } catch {
    /* ignore */
  }
  mediaRecorder = null
}

async function startAudioCapture() {
  if (!shouldUseAudioStreaming.value || !canCaptureCandidateTurn.value || mediaRecorder) return

  try {
    if (!mediaStream) {
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
    }

    const silenceDetectionReady = startAudioSilenceDetection(mediaStream)

    const options = typeof window.MediaRecorder !== 'undefined' && window.MediaRecorder.isTypeSupported(AUDIO_MIME_TYPE)
      ? { mimeType: AUDIO_MIME_TYPE }
      : undefined

    mediaRecorder = options ? new MediaRecorder(mediaStream, options) : new MediaRecorder(mediaStream)

    nextAudioSeq = 0
    sentAudioEnd = false

    const codec = mediaRecorder.mimeType?.includes('opus') ? 'webm-opus' : 'pcm16'
    const sampleRate = getMediaSampleRate(mediaStream)

    mediaRecorder.onstart = () => {
      sendWsMessage({ type: 'audio_start', codec, sample_rate_hz: sampleRate })
    }

    mediaRecorder.ondataavailable = async (event: BlobEvent) => {
      if (!event.data || event.data.size === 0) return
      if (ws?.readyState !== WebSocket.OPEN) return
      const data_b64 = await blobToBase64(event.data)
      sendWsMessage({
        type: 'audio_chunk',
        data_b64,
        seq: nextAudioSeq,
        is_final: false,
      })
      nextAudioSeq += 1
    }

    mediaRecorder.onerror = () => {
      audioStreamingEnabled.value = false
      stopAudioSilenceDetection()
      mediaRecorder = null
      startListening()
    }

    mediaRecorder.onstop = () => {
      stopAudioSilenceDetection()
      mediaRecorder = null
      clearAudioTurnTimer()
    }

    mediaRecorder.start(AUDIO_CHUNK_SLICE_MS)

    clearAudioTurnTimer()
    audioTurnTimer = window.setTimeout(() => {
      stopAudioCapture({ sendEnd: true, awaitBackend: true })
    }, silenceDetectionReady ? AUDIO_MAX_TURN_DURATION_MS : AUDIO_FALLBACK_TURN_DURATION_MS)
  } catch {
    stopAudioSilenceDetection()
    audioStreamingEnabled.value = false
    startListening()
  }
}

function startListening() {
  if (
    shouldUseAudioStreaming.value
    || !SpeechRecognitionAPI
    || speechRecognitionDisabled.value
    || recognition
    || !canCaptureCandidateTurn.value
  ) return

  const Rec = (window as unknown as { SpeechRecognition?: SpeechRecognitionCtor }).SpeechRecognition
    || (window as unknown as { webkitSpeechRecognition?: SpeechRecognitionCtor }).webkitSpeechRecognition
  if (!Rec) return
  recognition = new Rec()
  recognition.continuous = true
  recognition.interimResults = true
  recognition.lang = 'en-US'
  recognition.maxAlternatives = 1

  clearSpeechCaptureBuffer()
  recognition.onresult = (event: any) => {
    const transcriptChunk = extractSpeechTranscript(event)
    if (!transcriptChunk) return

    pendingSpeechTranscript = transcriptChunk
    clearPendingSpeechDebounceTimer()
    pendingSpeechDebounceTimer = window.setTimeout(() => {
      pendingSpeechDebounceTimer = null
      const finalTranscript = pendingSpeechTranscript.trim()
      if (!finalTranscript || !canCaptureCandidateTurn.value) return
      sendCandidateText(finalTranscript)
      stopListening()
    }, SPEECH_RESULT_DEBOUNCE_MS)
  }
  recognition.onend = () => {
    recognition = null
    if (pendingSpeechDebounceTimer) return

    if (canCaptureCandidateTurn.value && !speechRecognitionDisabled.value) {
      if (pendingRestartTimer) window.clearTimeout(pendingRestartTimer)
      pendingRestartTimer = window.setTimeout(() => {
        pendingRestartTimer = null
        startListening()
      }, 400)
    }
  }
  recognition.onerror = (event: any) => {
    const err = event.error
    if (
      err === 'not-allowed'
      || err === 'service-not-allowed'
      || err === 'language-not-supported'
      || err === 'audio-capture'
    ) {
      speechRecognitionDisabled.value = true
    }
    clearSpeechCaptureBuffer()
    recognition = null
  }
  try {
    recognition.start()
  } catch {
    speechRecognitionDisabled.value = true
    clearSpeechCaptureBuffer()
    recognition = null
  }
}

function stopListening() {
  if (pendingRestartTimer) {
    window.clearTimeout(pendingRestartTimer)
    pendingRestartTimer = null
  }
  clearSpeechCaptureBuffer()
  if (recognition) {
    try {
      recognition.stop()
    } catch {
      /* ignore */
    }
    recognition = null
  }
}

function triggerCandidateCaptureIfReady() {
  if (!canCaptureCandidateTurn.value) return
  if (shouldUseAudioStreaming.value) {
    startAudioCapture()
  } else {
    startListening()
  }
}

watch(callSubstatus, (sub) => {
  if (sub === 'listening') {
    awaitingBackendTurn.value = false
    triggerCandidateCaptureIfReady()
  }
  if (sub === 'emma_speaking') {
    awaitingBackendTurn.value = false
    stopListening()
    stopAudioCapture({ sendEnd: false, awaitBackend: false })
  }
})

if (typeof window !== 'undefined' && window.speechSynthesis) {
  window.speechSynthesis.onvoiceschanged = () => {
    preferredEmmaVoice = getPreferredEmmaVoice()
  }
}

async function onConsentAccepted() {
  consentAccepted.value = true
  wsError.value = null
  callStatus.value = 'connecting'

  const mic = await requestMicrophonePermission()
  if (!mic.granted) {
    callStatus.value = 'idle'
    wsError.value = mic.reason || 'Microphone permission is required to start the call.'
    return
  }

  const speechCaptureAvailable = !!SpeechRecognitionAPI
  const wsAudioCaptureAvailable = WS_AUDIO_STREAMING_FORCE && canUseMediaRecorder.value
  if (!speechCaptureAvailable && !wsAudioCaptureAvailable) {
    callStatus.value = 'idle'
    wsError.value = 'Voice capture is unavailable in this browser. Use a Chromium browser or enable backend audio streaming.'
    return
  }
  microphoneGranted.value = true
  speechRecognitionDisabled.value = !SpeechRecognitionAPI

  const id = applicationId.value
  if (!id) {
    callStatus.value = 'idle'
    wsError.value = 'Invalid application'
    return
  }
  const url = wsCallUrl(id)
  ws = new WebSocket(url)
  ws.onopen = () => {
    callStatus.value = 'connected'
    callSubstatus.value = null
  }
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data) as ServerControlMessage | ServerTextMessage | ServerAudioChunkMessage
      if (data?.type === 'control') {
        const ev = data.event
        if (ev === 'call_ended') {
          stopListening()
          stopAudioCapture({ sendEnd: false, awaitBackend: false })
          if (typeof window !== 'undefined' && window.speechSynthesis) window.speechSynthesis.cancel()
          callStatus.value = 'ended'
          showPostCallModal.value = true
        } else if (ev === 'emma_speaking' || ev === 'listening') {
          awaitingBackendTurn.value = false
          callSubstatus.value = ev
        }
      } else if (data?.type === 'text' && typeof data.text === 'string') {
        appendTranscriptLine(data.text, typeof data.speaker === 'string' ? data.speaker : undefined)
        if (data.speaker !== 'candidate') speak(data.text)
      } else if (data?.type === 'audio_chunk' && data.speaker === 'emma') {
        emmaAudioSpeaking.value = true
        if (data.is_final) {
          emmaAudioSpeaking.value = false
          triggerCandidateCaptureIfReady()
        }
      }
    } catch {
      // ignore non-JSON
    }
  }
  ws.onclose = (event) => {
    ws = null
    stopListening()
    stopAudioCapture({ sendEnd: false, awaitBackend: false })
    releaseMediaStream()
    if (typeof window !== 'undefined' && window.speechSynthesis) window.speechSynthesis.cancel()
    if (callStatus.value === 'ended' && showPostCallModal.value) return
    if (event.wasClean && event.code === 1000) {
      callStatus.value = 'ended'
      showPostCallModal.value = true
      return
    }
    callStatus.value = 'ended'
    if (event.code === 4000) wsError.value = 'Invalid application'
    else if (event.code === DUPLICATE_CALL_CLOSE_CODE) wsError.value = 'A call is already in progress for this application'
    else wsError.value = 'Could not connect to call'
  }
  ws.onerror = () => {
    if (!wsError.value) wsError.value = 'Could not connect to call'
  }
}

function onEndCall() {
  stopListening()
  stopAudioCapture({ sendEnd: false, awaitBackend: false })
  releaseMediaStream()
  if (typeof window !== 'undefined' && window.speechSynthesis) window.speechSynthesis.cancel()
  if (ws?.readyState === WebSocket.OPEN) ws.close(1000)
  callStatus.value = 'ended'
  showPostCallModal.value = true
}

onBeforeUnmount(() => {
  stopListening()
  stopAudioCapture({ sendEnd: false, awaitBackend: false })
  releaseMediaStream()
  if (typeof window !== 'undefined' && window.speechSynthesis) {
    window.speechSynthesis.cancel()
  }
  emmaAudioSpeaking.value = false
  if (ws) {
    ws.close()
    ws = null
  }
})
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
      <BaseCard v-else-if="wsError" class="w-full max-w-lg">
        <h1 class="text-h2 mb-4 text-text-primary">Call unavailable</h1>
        <p class="mb-4 text-body text-text-primary" role="alert">{{ wsError }}</p>
        <a
          href="/application"
          class="inline-block rounded px-4 py-2 font-button text-button text-brand underline focus:outline-none focus:ring-2 focus:ring-brand"
          aria-label="Go to application"
        >
          Go to application
        </a>
      </BaseCard>
      <BaseCard v-else class="w-full max-w-lg">
        <h1 class="text-h2 mb-6 text-text-primary">Screening call</h1>
        <CallUI
          :status="callStatus"
          :substatus="callSubstatus"
          :transcript="transcript"
          :emma-speaking="emmaAudioSpeaking"
          @end-call="onEndCall"
        />

        <div v-if="callStatus === 'connected'" class="mt-4 flex flex-col gap-3">
          <p class="text-body-small text-text-accent">
            Speak when the status says “Your turn — speak now”.
          </p>
        </div>
      </BaseCard>
      <PostCallModal
        :open="showPostCallModal"
        :application-id="applicationId"
      />
    </template>
  </div>
</template>
