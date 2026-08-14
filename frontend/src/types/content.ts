export interface BanlistVersion {
  id: string
  version: string
  major_version: number
  minor_version: number
  title: string
  content_html: string
  published_at: string
}

export interface Announcement {
  id: string
  title: string
  content_html: string
  is_pinned: boolean
  published_at: string
  updated_at: string
}

export interface ListResponse<T> {
  items: T[]
  total: number
}

export interface ImageUploadResponse {
  url: string
  width: number
  height: number
  content_type: string
}
