import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import AnalysisPage from './AnalysisPage.vue'
import FitScoreDisplay from '../components/FitScoreDisplay.vue'

vi.mock('../api/client', () => {
  const ApiError = class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.name = 'ApiError'
      this.status = status
    }
  }
  return {
    getAnalysis: vi.fn(),
    ApiError,
  }
})

const { getAnalysis, ApiError } = await import('../api/client')

describe('AnalysisPage', () => {
  beforeEach(() => {
    vi.mocked(getAnalysis).mockReset()
  })

  it('shows result when getAnalysis returns 200', async () => {
    vi.mocked(getAnalysis).mockResolvedValue({
      fit_score: 78,
      skills: ['Python', 'Communication'],
    })
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/analysis', name: 'analysis', component: AnalysisPage },
      ],
    })
    await router.push({ path: '/analysis', query: { application_id: 'app-123' } })
    const wrapper = mount(AnalysisPage, {
      global: { plugins: [router] },
    })
    await vi.waitFor(() => {
      expect(wrapper.findComponent(FitScoreDisplay).exists()).toBe(true)
    }, { timeout: 2000 })
    expect(wrapper.findComponent(FitScoreDisplay).props('score')).toBe(78)
    expect(getAnalysis).toHaveBeenCalledWith('app-123')
  })

  it('polls on 202 then shows result on 200', async () => {
    vi.useFakeTimers()
    vi.mocked(getAnalysis)
      .mockRejectedValueOnce(new ApiError('Analysis pending', 202))
      .mockResolvedValueOnce({ fit_score: 90, skills: ['TypeScript'] })
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/analysis', component: AnalysisPage }],
    })
    await router.push({ path: '/analysis', query: { application_id: 'app-1' } })
    const wrapper = mount(AnalysisPage, { global: { plugins: [router] } })
    await vi.advanceTimersByTimeAsync(2600)
    await wrapper.vm.$nextTick()
    expect(vi.mocked(getAnalysis).mock.calls.length).toBeGreaterThanOrEqual(2)
    await vi.waitFor(
      () => {
        expect(wrapper.findComponent(FitScoreDisplay).exists()).toBe(true)
        expect(wrapper.findComponent(FitScoreDisplay).props('score')).toBe(90)
      },
      { timeout: 2000 }
    )
    vi.useRealTimers()
  })

  it('shows Application not found on 404', async () => {
    vi.mocked(getAnalysis).mockRejectedValue(new ApiError('Application not found', 404))
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/analysis', component: AnalysisPage }],
    })
    await router.push({ path: '/analysis', query: { application_id: 'bad-id' } })
    const wrapper = mount(AnalysisPage, { global: { plugins: [router] } })
    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('Application not found')
    }, { timeout: 2000 })
  })
})
