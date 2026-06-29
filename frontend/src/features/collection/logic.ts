import type { MangaItem } from "@/lib/types"
import type { DownloadState } from "@/hooks/use-downloads"

export type SortMode =
  | "default"
  | "title-asc"
  | "title-desc"
  | "pages-desc"
  | "pages-asc"
  | "status"

export const SORT_OPTIONS: { value: SortMode; label: string }[] = [
  { value: "default", label: "默认排序" },
  { value: "title-asc", label: "标题 A→Z" },
  { value: "title-desc", label: "标题 Z→A" },
  { value: "pages-desc", label: "页数 多→少" },
  { value: "pages-asc", label: "页数 少→多" },
  { value: "status", label: "按状态" },
]

export type MangaStatus = "downloading" | "pending" | "downloaded"

export function statusOf(m: MangaItem, downloads: Record<string, DownloadState>): MangaStatus {
  if (downloads[m.id]) return "downloading"
  if (m.is_downloaded) return "downloaded"
  return "pending"
}

// 状态排序优先级：下载中 → 待下载 → 已下载
const STATUS_ORDER: Record<MangaStatus, number> = {
  downloading: 0,
  pending: 1,
  downloaded: 2,
}

export function filterMangas(mangas: MangaItem[], query: string): MangaItem[] {
  const q = query.trim().toLowerCase()
  if (!q) return mangas
  return mangas.filter(
    (m) =>
      m.title.toLowerCase().includes(q) || (m.author || "").toLowerCase().includes(q)
  )
}

export function sortMangas(
  mangas: MangaItem[],
  sort: SortMode,
  downloads: Record<string, DownloadState>
): MangaItem[] {
  if (sort === "default") return mangas
  const arr = [...mangas]
  switch (sort) {
    case "title-asc":
      return arr.sort((a, b) => a.title.localeCompare(b.title, "zh"))
    case "title-desc":
      return arr.sort((a, b) => b.title.localeCompare(a.title, "zh"))
    case "pages-desc":
      return arr.sort((a, b) => (b.page_count ?? 0) - (a.page_count ?? 0))
    case "pages-asc":
      return arr.sort((a, b) => (a.page_count ?? 0) - (b.page_count ?? 0))
    case "status":
      return arr.sort(
        (a, b) => STATUS_ORDER[statusOf(a, downloads)] - STATUS_ORDER[statusOf(b, downloads)]
      )
    default:
      return arr
  }
}

export interface AuthorGroup {
  author: string
  mangas: MangaItem[]
}

// 按作者分组（保持出现顺序）
export function groupByAuthor(mangas: MangaItem[]): AuthorGroup[] {
  const groups: AuthorGroup[] = []
  const index = new Map<string, AuthorGroup>()
  for (const m of mangas) {
    const author = m.author || "未知作者"
    let g = index.get(author)
    if (!g) {
      g = { author, mangas: [] }
      index.set(author, g)
      groups.push(g)
    }
    g.mangas.push(m)
  }
  return groups
}
