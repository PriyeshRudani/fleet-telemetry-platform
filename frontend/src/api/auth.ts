import { apiRequest } from './client'
import type { CurrentUser, LoginRequest, TokenResponse } from '../types/auth'

export function loginRequest(credentials: LoginRequest): Promise<TokenResponse> {
  return apiRequest<TokenResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(credentials),
  })
}

export function getCurrentUser(token: string): Promise<CurrentUser> {
  return apiRequest<CurrentUser>('/users/me', { token })
}