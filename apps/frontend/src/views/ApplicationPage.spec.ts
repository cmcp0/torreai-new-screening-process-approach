import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import ApplicationPage from './ApplicationPage.vue'

vi.mock('../api/client', () => ({
  createApplication: vi.fn(),
}))

const { createApplication } = await import('../api/client')

describe('ApplicationPage', () => {
  beforeEach(() => {
    vi.mocked(createApplication).mockReset()
  })

  it('does not redirect when user navigates away before createApplication resolves', async () => {
    let resolveMock: (value: { application_id: string }) => void
    const createPromise = new Promise<{ application_id: string }>((resolve) => {
      resolveMock = resolve
    })
    vi.mocked(createApplication).mockReturnValue(createPromise)

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/application', name: 'application', component: ApplicationPage },
        { path: '/call', name: 'call', component: { template: '<div>Call</div>' } },
      ],
    })
    await router.push({
      path: '/application',
      query: { username: 'john', job_offer_id: 'abc123' },
    })

    const replaceSpy = vi.spyOn(router, 'replace')

    const wrapper = mount(ApplicationPage, {
      global: {
        plugins: [router],
      },
    })

    await wrapper.vm.$nextTick()

    wrapper.unmount()

    resolveMock!({ application_id: 'mock-app-1' })
    await createPromise

    expect(replaceSpy).not.toHaveBeenCalled()
  })
})
