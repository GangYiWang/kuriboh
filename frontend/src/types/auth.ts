export type Role = 'USER' | 'PLATFORM_ADMIN'

export interface User {
  id: string
  phone_number: string | null
  qq_number: string | null
  nickname: string
  role: Role
  qq_bound: boolean
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: 'bearer'
  user: User
}

export interface QqOAuthStatus {
  configured: boolean
  authorization_url: string | null
  state: string | null
}
