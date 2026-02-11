const configuredBase =
  typeof import.meta.env.VITE_API_BASE_URL === 'string'
    ? import.meta.env.VITE_API_BASE_URL.trim()
    : ''

const normalizedConfiguredBase = configuredBase.replace(/\/$/, '')
const defaultBase =
  typeof window !== 'undefined' ? window.location.origin : 'http://localhost:8000'

export const apiBaseUrl = (normalizedConfiguredBase || defaultBase).replace(/\/$/, '')

function toWsBase(baseUrl: string): string {
  const trimmed = baseUrl.replace(/\/$/, '')
  if (trimmed.startsWith('ws://') || trimmed.startsWith('wss://')) {
    return trimmed
  }
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    return trimmed.replace(/^http/, 'ws')
  }
  if (typeof window !== 'undefined') {
    const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws'
    return `${scheme}://${window.location.host}`
  }
  return 'ws://localhost:8000'
}

export function wsCallUrl(applicationId: string): string {
  const wsBase = toWsBase(normalizedConfiguredBase || defaultBase)
  return `${wsBase}/api/ws/call?application_id=${encodeURIComponent(applicationId)}`
}
