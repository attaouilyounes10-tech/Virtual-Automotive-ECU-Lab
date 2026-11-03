export interface SimulationStatus {
  running: boolean
  paused: boolean
  current_time: number
  elapsed_time: number
  vehicle_state: Record<string, any>
}

export interface SimulationControlResponse {
  success: boolean
  message: string
  state?: SimulationStatus
}