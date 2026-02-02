import type { ApplicationParams, ApplicationResult, AnalysisResult } from '../types'

/** Create application (mock): ~800 ms delay, returns application_id. Invalid params → reject. */
export function createApplication(params: ApplicationParams): Promise<ApplicationResult> {
  return new Promise((resolve, reject) => {
    const username = (params.username ?? '').trim()
    const job_offer_id = (params.job_offer_id ?? '').trim()
    if (!username || !job_offer_id) {
      reject(new Error('Username and job offer are required'))
      return
    }
    setTimeout(() => {
      resolve({ application_id: `mock-app-${Date.now()}` })
    }, 800)
  })
}

/** Get analysis (mock): ~2–3 s delay, returns fit_score and skills. */
export function getAnalysis(application_id: string): Promise<AnalysisResult> {
  return new Promise((resolve, reject) => {
    if (!application_id?.trim()) {
      reject(new Error('application_id is required'))
      return
    }
    const delay = 2000 + Math.random() * 1000
    setTimeout(() => {
      resolve({
        fit_score: 78,
        skills: ['Python', 'Communication', 'Problem solving'],
      })
    }, delay)
  })
}
