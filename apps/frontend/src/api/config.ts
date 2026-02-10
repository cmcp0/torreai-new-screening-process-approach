const base = typeof import.meta.env.VITE_API_BASE_URL === 'string' && import.meta.env.VITE_API_BASE_URL.trim()
  ? import.meta.env.VITE_API_BASE_URL.trim().replace(/\/$/, '')
  : 'http://localhost:8000'

export const apiBaseUrl = base

export function wsCallUrl(applicationId: string): string {
  const wsBase = base.replace(/^http/, 'ws')
  return `${wsBase}/api/ws/call?application_id=${encodeURIComponent(applicationId)}`
}
