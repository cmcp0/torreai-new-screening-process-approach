/* Mock / types for Phase 1; align with backend DTOs in Phase 3 */

export interface ApplicationParams {
  username: string
  job_offer_id: string
}

export interface ApplicationResult {
  application_id: string
}

export type CallStatus = 'idle' | 'connecting' | 'connected' | 'ended'

export interface CallState {
  status: CallStatus
  applicationId: string | null
}

export interface AnalysisResult {
  fit_score: number // 0–100, display as percentage
  skills: string[]
}
