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
