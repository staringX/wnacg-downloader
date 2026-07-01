import { useCallback, useEffect, useState } from "react"
import { mangaApi, recentUpdatesApi, settingsApi } from "@/lib/api"
import type { AppConfig } from "@/lib/api"
import type { MangaItem, RecentUpdate } from "@/lib/types"

// 收藏夹 / 最近更新 / 设置 的数据加载
export function useAppData() {
  const [mangas, setMangas] = useState<MangaItem[]>([])
  const [recentUpdates, setRecentUpdates] = useState<RecentUpdate[]>([])
  const [settings, setSettings] = useState<AppConfig>({
    manual_manga_site_url: null,
    recent_updates_hanhua_only: true,
    collection_synced_at: null,
    recent_synced_at: null,
  })
  const [loading, setLoading] = useState(true)

  const refetchMangas = useCallback(async () => {
    const res = await mangaApi.fetchMangas()
    if (res.success && res.data) setMangas(res.data)
  }, [])

  const refetchUpdates = useCallback(async () => {
    const res = await recentUpdatesApi.fetchRecentUpdates()
    if (res.success && res.data) setRecentUpdates(res.data)
  }, [])

  const refetchSettings = useCallback(async () => {
    try {
      const cfg = await settingsApi.getSettings()
      setSettings(cfg)
    } catch {
      /* 忽略：使用默认值 */
    }
  }, [])

  useEffect(() => {
    let active = true
    ;(async () => {
      setLoading(true)
      await Promise.all([refetchMangas(), refetchUpdates(), refetchSettings()])
      if (active) setLoading(false)
    })()
    return () => {
      active = false
    }
  }, [refetchMangas, refetchUpdates, refetchSettings])

  return {
    mangas,
    recentUpdates,
    settings,
    setSettings,
    loading,
    refetchMangas,
    refetchUpdates,
    refetchSettings,
    // 本地乐观移除（删除后立即从列表去除）
    removeManga: (id: string) => setMangas((prev) => prev.filter((m) => m.id !== id)),
    removeMangas: (ids: string[]) =>
      setMangas((prev) => prev.filter((m) => !ids.includes(m.id))),
  }
}
