export interface TelemetryResponse {
  speed_kmh: number
  target_speed_kmh: number
  acceleration_mps2: number
  throttle_position_pct: number
  brake_pressure_bar: number
  obstacle_detected: boolean
  obstacle_distance_m: number
  relative_speed_mps: number
  collision_risk_level: number
  fcw_active: boolean
  aeb_active: boolean
}