import { apiRequest } from './client'
import type { Vehicle } from '../types/vehicle'

export function getVehicles(token: string): Promise<Vehicle[]> {
  return apiRequest<Vehicle[]>('/vehicles', { token })
}