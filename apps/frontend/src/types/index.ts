/* Mock / types for Phase 1; align with backend DTOs in Phase 3 */

export interface ApplicationParams {
  username: string
  job_offer_id: string
}

export interface ApplicationResult {
  application_id: string
}

export type CallStatus = 'idle' | 'connecting' | 'connected' | 'ended'

/** Control event from WebSocket: who is speaking or listening. */
export type CallSubstatus = 'emma_speaking' | 'listening' | null

export interface CallState {
  status: CallStatus
  applicationId: string | null
}

export interface AnalysisResult {
  fit_score: number // 0–100, display as percentage
  skills: string[]
  /** True when analysis could not be completed after retries */
  failed?: boolean
}
