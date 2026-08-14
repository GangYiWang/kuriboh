export interface HealthResponse {
  status: 'ok'
  service: string
  database: 'ok'
  version: string
}

export interface ApiErrorBody {
  code: string
  message: string
  details: unknown | null
  request_id: string
}
