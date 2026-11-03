export interface HealthResponse {
  status: string
  service: string
  version: string
  simulation?: {
    running: boolean
    paused: boolean
  }
}