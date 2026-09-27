export interface RoutePoint {
  latitude: number
  longitude: number
}

export interface PlannedRoute {
  id: number
  trip_id: number
  filename: string
  route_format: string
  points: RoutePoint[]
  point_count: number
  uploaded_at: string
}

export interface RouteDeviationStatus {
  has_route: boolean
  currently_deviated: boolean
  last_distance_meters: number | null
  threshold_meters: number
  last_checked_at: string | null
  last_alert_at: string | null
}