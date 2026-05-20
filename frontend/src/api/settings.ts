import { get } from "./client"

export interface AppSettings {
  debug: boolean
  fx_api_key_configured: boolean
  newsapi_key_configured: boolean
  sentiment_enabled: boolean
  database_url: string
  scheduler_jobs: { id: string; name: string; interval: string }[]
}

export function fetchAppSettings(): Promise<AppSettings> {
  return get<AppSettings>("/api/v1/settings")
}
