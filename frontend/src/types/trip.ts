export type TripStatus = 'ACTIVE' | 'COMPLETED'

export interface Trip {
  id: number
  vehicle_id: number
  started_at: string
  ended_at: string | null
  status: TripStatus
}