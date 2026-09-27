import { apiRequest } from './client'
import type { Trip } from '../types/trip'

export function getTrips(token: string): Promise<Trip[]> {
  return apiRequest<Trip[]>('/trips', { token })
}

export function startTrip(token: string, vehicleId: number): Promise<Trip> {
  return apiRequest<Trip>('/trips/start', {
    method: 'POST',
    token,
    body: JSON.stringify({ vehicle_id: vehicleId }),
  })
}

export function stopTrip(token: string, tripId: number): Promise<Trip> {
  return apiRequest<Trip>(`/trips/${tripId}/stop`, {
    method: 'POST',
    token,
  })
}