import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import CallPage from './CallPage.vue'

class MockSpeechRecognition {
  continuous = false
  interimResults = false
  lang = 'en-US'
  maxAlternatives = 1

  onresult: ((ev: unknown) => void) | null = null
  onend: ((ev: unknown) => void) | null = null
  onerror: ((ev: unknown) => void) | null = null

  start() {}

  stop() {}
}

class MockWebSocket {
  static instances: MockWebSocket[] = []
  static OPEN = 1
  static CLOSED = 3

  readyState = 0
  sent: string[] = []
  onopen: ((ev: Event) => void) | null = null
  onmessage: ((ev: MessageEvent) => void) | null = null
  onclose: ((ev: CloseEvent) => void) | null = null
  onerror: ((ev: Event) => void) | null = null

  url: string

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
  }

  open() {
    this.readyState = 1
    this.onopen?.(new Event('open'))
  }

  send(data: string) {
    this.sent.push(data)
  }

  emit(payload: unknown) {
    this.onmessage?.({ data: JSON.stringify(payload) } as MessageEvent)
  }

  close(code = 1000) {
    this.readyState = 3
    this.onclose?.({ code, wasClean: true } as CloseEvent)
  }

  closeWith(code: number, wasClean = false) {
    this.readyState = 3
    this.onclose?.({ code, wasClean } as CloseEvent)
  }
}

async function buildWrapper() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div>Home</div>' } },
      { path: '/call', component: CallPage },
    ],
  })

  await router.push({ path: '/call', query: { application: 'app-1' } })
  await router.isReady()

  const wrapper = mount(CallPage, {
    global: {
      plugins: [router],
      stubs: {
        ConsentForm: {
          emits: ['accepted'],
          template: '<button aria-label="Accept consent" @click="$emit(\'accepted\')">Accept</button>',
        },
      },
    },
  })

  return { wrapper, router }
}

describe('CallPage', () => {
  beforeEach(() => {
    MockWebSocket.instances.length = 0
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
    vi.stubGlobal('SpeechRecognition', MockSpeechRecognition as unknown as { new (): any })
    vi.stubGlobal('webkitSpeechRecognition', undefined)
    Object.defineProperty(window, 'isSecureContext', {
      configurable: true,
      value: true,
    })
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: {
        getUserMedia: vi.fn(async () => ({
          getTracks: () => [{ stop: vi.fn() }],
        })),
      },
    })
  })

  it('is voice-only and does not render candidate text input fallback', async () => {
    const { wrapper } = await buildWrapper()

    await wrapper.find('button[aria-label="Accept consent"]').trigger('click')
    await Promise.resolve()

    const socket = MockWebSocket.instances[0]
    expect(socket).toBeTruthy()
    if (!socket) throw new Error('Expected websocket instance')
    socket.open()
    socket.emit({ type: 'control', event: 'listening' })
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()

    expect(wrapper.find('#text-fallback-reply').exists()).toBe(false)
    expect(wrapper.find('button[aria-label="Send text reply"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Speak when the status says “Your turn — speak now”.')
  })

  it('shows duplicate-call error when websocket closes with 4409', async () => {
    const { wrapper } = await buildWrapper()

    await wrapper.find('button[aria-label="Accept consent"]').trigger('click')

    const socket = MockWebSocket.instances[0]
    if (!socket) throw new Error('Expected websocket instance')
    socket.open()
    socket.closeWith(4409, false)
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('A call is already in progress for this application')
  })

  it('shows microphone-required error and does not connect call when permission is denied', async () => {
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: {
        getUserMedia: vi.fn(async () => {
          throw new Error('Permission denied')
        }),
      },
    })

    const { wrapper } = await buildWrapper()
    await wrapper.find('button[aria-label="Accept consent"]').trigger('click')
    await Promise.resolve()
    await wrapper.vm.$nextTick()

    expect(MockWebSocket.instances).toHaveLength(0)
    expect(wrapper.text()).toContain('Microphone permission is required.')
  })
})
