export interface TelemetryEvent {
  event: 'telemetry'
  vehicle_id: number
  device_id: string
  trip_id: number
  organization_id: number
  recorded_at: string
  temperature: number
  humidity: number
  dew_point: number
  elevation: number
  latitude: number
  longitude: number
}