export interface Vehicle {
  id: number
  organization_id: number
  name: string
  device_id: string
  is_online: boolean
  latest_latitude: number | null
  latest_longitude: number | null
  last_seen_at: string | null
  created_at: string
}