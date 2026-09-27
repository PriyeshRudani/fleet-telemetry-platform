import { ApiError, apiRequest } from './client'
import type { PlannedRoute, RouteDeviationStatus } from '../types/route'

export function getTripRoute(token: string, tripId: number): Promise<PlannedRoute> {
  return apiRequest<PlannedRoute>(`/trips/${tripId}/route`, { token })
}

export function getTripRouteStatus(token: string, tripId: number): Promise<RouteDeviationStatus> {
  return apiRequest<RouteDeviationStatus>(`/trips/${tripId}/route/status`, { token })
}

export function uploadTripRoute(token: string, tripId: number, file: File): Promise<PlannedRoute> {
  const formData = new FormData()
  formData.append('file', file)
  return apiRequest<PlannedRoute>(`/trips/${tripId}/route`, {
    method: 'POST',
    token,
    body: formData,
  })
}

export function isMissingRouteError(error: unknown) {
  return error instanceof ApiError && error.status === 404
}