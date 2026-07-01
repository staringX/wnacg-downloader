import type { MangaItem } from "@/lib/types"
import type { DownloadState } from "@/hooks/use-downloads"

export type MangaStatus = "downloading" | "pending" | "downloaded"

export function statusOf(m: MangaItem, downloads: Record<string, DownloadState>): MangaStatus {
  if (downloads[m.id]) return "downloading"
  if (m.is_downloaded) return "downloaded"
  return "pending"
}

export const UNKNOWN_AUTHOR = "未知作者"

export function filterMangas(mangas: MangaItem[], query: string): MangaItem[] {
  const q = query.trim().toLowerCase()
  if (!q) return mangas
  return mangas.filter(
    (m) =>
      m.title.toLowerCase().includes(q) || (m.author || "").toLowerCase().includes(q)
  )
}

// 出现顺序を保った一意な作者名リスト（フィルタ選択肢用）
export function uniqueAuthors(mangas: MangaItem[]): string[] {
  const set = new Set<string>()
  for (const m of mangas) set.add(m.author || UNKNOWN_AUTHOR)
  return Array.from(set).sort((a, b) => a.localeCompare(b, "zh"))
}

// 選択された作者のみ残す（未選択＝全件）
export function filterByAuthors<T extends MangaItem>(mangas: T[], selected: Set<string>): T[] {
  if (selected.size === 0) return mangas
  return mangas.filter((m) => selected.has(m.author || UNKNOWN_AUTHOR))
}

// リリース時間（updated_at）の新しい順に並べる。日付なしは末尾。
export function sortByRelease<T extends MangaItem>(mangas: T[]): T[] {
  return [...mangas].sort((a, b) => {
    const ta = a.updated_at ? Date.parse(a.updated_at) : 0
    const tb = b.updated_at ? Date.parse(b.updated_at) : 0
    return tb - ta
  })
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
