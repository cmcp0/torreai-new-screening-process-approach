import { apiBaseUrl } from './config'
import type { ApplicationParams, ApplicationResult, AnalysisResult } from '../types'

const APPLICATION_CREATE_TIMEOUT_MS = 30_000
const ANALYSIS_FETCH_TIMEOUT_MS = 10_000

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public body?: unknown
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

function parseDetail(body: unknown): string | null {
  if (body == null || typeof body !== 'object') return null
  const d = (body as { detail?: unknown }).detail
  if (typeof d === 'string') return d
  if (Array.isArray(d) && d.length > 0) {
    const first = d[0]
    if (typeof first === 'string') return first
    if (first && typeof first === 'object' && 'msg' in first) return String((first as { msg: unknown }).msg)
  }
  return null
}

function genericMessage(status: number): string {
  if (status === 404) return 'Not found'
  if (status >= 500) return 'Service unavailable'
  if (status === 400) return 'Bad request'
  if (status === 422) return 'Invalid data'
  return 'Request failed'
}

export async function createApplication(params: ApplicationParams): Promise<ApplicationResult> {
  const username = (params.username ?? '').trim()
  const job_offer_id = (params.job_offer_id ?? '').trim()
  if (!username || !job_offer_id) {
    throw new Error('Username and job offer are required')
  }

  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), APPLICATION_CREATE_TIMEOUT_MS)
  let body: unknown
  let status: number
  try {
    const res = await fetch(`${apiBaseUrl}/api/applications`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, job_offer_id }),
      signal: controller.signal,
    })
    status = res.status
    const text = await res.text()
    body = text ? JSON.parse(text) : undefined
    if (res.ok) {
      const data = body as { application_id?: string }
      if (typeof data?.application_id === 'string') {
        return { application_id: data.application_id }
      }
      throw new ApiError('Invalid response', status, body)
    }
  } catch (e) {
    if (e instanceof ApiError) throw e
    if (e instanceof SyntaxError) {
      throw new ApiError(genericMessage(status!), status!, body)
    }
    if (e instanceof Error && e.name === 'AbortError') {
      throw new ApiError('Service unavailable', 0, undefined)
    }
    throw new ApiError('Failed to create application', 0, undefined)
  } finally {
    clearTimeout(timeout)
  }

  const detail = parseDetail(body)
  throw new ApiError(detail ?? genericMessage(status), status, body)
}

export async function getAnalysis(application_id: string): Promise<AnalysisResult> {
  const id = (application_id ?? '').trim()
  if (!id) {
    throw new Error('application_id is required')
  }

  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), ANALYSIS_FETCH_TIMEOUT_MS)
  let body: unknown
  let status: number
  try {
    const res = await fetch(`${apiBaseUrl}/api/applications/${encodeURIComponent(id)}/analysis`, {
      method: 'GET',
      signal: controller.signal,
    })
    status = res.status
    const text = await res.text()
    body = text ? JSON.parse(text) : undefined
    if (res.status === 200) {
      const data = body as { fit_score?: number; skills?: string[]; failed?: boolean }
      if (typeof data?.fit_score === 'number' && Array.isArray(data?.skills)) {
        return {
          fit_score: data.fit_score,
          skills: data.skills,
          failed: data?.failed === true,
        }
      }
      throw new ApiError('Invalid response', status, body)
    }
    if (res.status === 202) {
      throw new ApiError('Analysis pending', 202, body)
    }
  } catch (e) {
    if (e instanceof ApiError) throw e
    if (e instanceof SyntaxError) {
      throw new ApiError(genericMessage(status!), status!, body)
    }
    if (e instanceof Error && e.name === 'AbortError') {
      throw new ApiError('Service unavailable', 0, undefined)
    }
    throw new ApiError('Analysis failed', 0, undefined)
  } finally {
    clearTimeout(timeout)
  }

  const detail = parseDetail(body)
  throw new ApiError(detail ?? genericMessage(status), status, body)
}
