export interface CANFrameResponse {
  id: number
  data: string
  dlc: number
  is_rtr: boolean
  timestamp: number
}

export interface CANFramesResponse {
  frames: CANFrameResponse[]
  total: number
}