// 全局类型定义

export interface MangaItem {
  id: string
  title: string
  author: string
  manga_url: string
  file_size: number | null
  page_count: number | null
  updated_at: string | null
  downloaded_at?: string | null
  is_downloaded?: boolean
  preview_image_url?: string | null
  is_downloading?: boolean
}

export interface AuthorGroup {
  author: string
  mangas: MangaItem[]
}

export interface RecentUpdate extends MangaItem {
  is_downloaded: boolean
}

export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
}

export interface TaskStatus {
  id: string
  task_type: string
  status: "pending" | "running" | "completed" | "failed"
  progress: number
  total_items?: number
  completed_items: number
  message?: string
  error_message?: string
  manga_id?: string
  manga_ids?: string
  result_data?: string
  created_at: string
  updated_at: string
  completed_at?: string
}

