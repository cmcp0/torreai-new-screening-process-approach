import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createApplication, getAnalysis, ApiError } from './client'

describe('ApiError', () => {
  it('exposes message, status, and body', () => {
    const err = new ApiError('Not found', 404, { detail: 'Application not found' })
    expect(err.message).toBe('Not found')
    expect(err.status).toBe(404)
    expect(err.body).toEqual({ detail: 'Application not found' })
    expect(err.name).toBe('ApiError')
  })
})

describe('createApplication', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  it('throws when username or job_offer_id is empty', async () => {
    await expect(createApplication({ username: '', job_offer_id: 'x' })).rejects.toThrow(
      'Username and job offer are required'
    )
    await expect(createApplication({ username: 'u', job_offer_id: '' })).rejects.toThrow(
      'Username and job offer are required'
    )
  })

  it('returns application_id on 201', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ application_id: 'app-123' }), { status: 201 })
    )
    const result = await createApplication({ username: 'joe', job_offer_id: 'job-1' })
    expect(result).toEqual({ application_id: 'app-123' })
  })

  it('throws ApiError with detail on 404', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Torre user not found' }), { status: 404 })
    )
    await expect(createApplication({ username: 'joe', job_offer_id: 'job-1' })).rejects.toMatchObject({
      message: 'Torre user not found',
      status: 404,
    })
    await expect(createApplication({ username: 'joe', job_offer_id: 'job-1' })).rejects.toBeInstanceOf(ApiError)
  })

  it('throws ApiError with first element when detail is array', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: ['First error', 'Second'] }), { status: 422 })
    )
    await expect(createApplication({ username: 'joe', job_offer_id: 'job-1' })).rejects.toMatchObject({
      message: 'First error',
      status: 422,
    })
  })

  it('throws generic message when detail missing (5xx)', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockResolvedValue(new Response(JSON.stringify({}), { status: 503 }))
    await expect(createApplication({ username: 'joe', job_offer_id: 'job-1' })).rejects.toMatchObject({
      message: 'Service unavailable',
      status: 503,
    })
  })

  it('throws on network failure', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockRejectedValue(new Error('Network error'))
    await expect(createApplication({ username: 'joe', job_offer_id: 'job-1' })).rejects.toMatchObject({
      message: 'Failed to create application',
      status: 0,
    })
  })
})

describe('getAnalysis', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  it('throws when application_id is empty', async () => {
    await expect(getAnalysis('')).rejects.toThrow('application_id is required')
    await expect(getAnalysis('   ')).rejects.toThrow('application_id is required')
  })

  it('returns fit_score and skills on 200', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ fit_score: 85, skills: ['Python', 'Go'] }), { status: 200 })
    )
    const result = await getAnalysis('app-1')
    expect(result).toEqual({ fit_score: 85, skills: ['Python', 'Go'], failed: false })
  })

  it('throws ApiError with status 202 when analysis pending', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Analysis pending' }), { status: 202 })
    )
    await expect(getAnalysis('app-1')).rejects.toMatchObject({
      message: 'Analysis pending',
      status: 202,
    })
    await expect(getAnalysis('app-1')).rejects.toBeInstanceOf(ApiError)
  })

  it('throws ApiError on 404', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Application not found' }), { status: 404 })
    )
    await expect(getAnalysis('app-1')).rejects.toMatchObject({
      message: 'Application not found',
      status: 404,
    })
  })

  it('throws generic message on 5xx when detail missing', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockResolvedValue(new Response(JSON.stringify({}), { status: 502 }))
    await expect(getAnalysis('app-1')).rejects.toMatchObject({
      message: 'Service unavailable',
      status: 502,
    })
  })
})
