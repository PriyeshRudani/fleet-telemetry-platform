export type UserRole = 'USER' | 'SUPER_ADMIN'

export interface LoginRequest {
  email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface CurrentUser {
  user_id: number
  email?: string
  role: UserRole
  organization_id: number | null
}