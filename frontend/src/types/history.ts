export interface HistoricalTelemetry {
  id: number
  trip_id: number
  vehicle_id: number
  recorded_at: string
  temperature: number
  humidity: number
  dew_point: number
  elevation: number
  latitude: number
  longitude: number
}