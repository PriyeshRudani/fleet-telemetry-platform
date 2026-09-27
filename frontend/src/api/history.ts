import { apiBlobRequest, apiRequest } from './client'
import type { HistoricalTelemetry } from '../types/history'

export function getTripTelemetry(token: string, tripId: number): Promise<HistoricalTelemetry[]> {
  return apiRequest<HistoricalTelemetry[]>(`/trips/${tripId}/telemetry`, { token })
}

export function exportTripTelemetry(token: string, tripId: number) {
  return apiBlobRequest(`/trips/${tripId}/telemetry/export`, { token })
}