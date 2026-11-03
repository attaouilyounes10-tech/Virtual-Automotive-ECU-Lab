import { TelemetryResponse } from './telemetry'

export interface WSMessage {
  type: string
  timestamp: string
  data: TelemetryResponse
}