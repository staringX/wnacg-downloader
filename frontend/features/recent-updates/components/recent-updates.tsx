// 最近更新组件
"use client"

import { useEffect, useMemo } from "react"
import { MangaCard } from "@/features/collection/components/manga-card"
import { AuthorSection } from "@/features/collection/components/author-section"
import { Sparkles } from "lucide-react"
import type { RecentUpdate, AuthorGroup, MangaItem } from "@/lib/types"
import { useRecentUpdates } from "../hooks/use-recent-updates"

interface RecentUpdatesProps {
  onDownload: (manga: RecentUpdate) => void
  onDelete: (manga: RecentUpdate) => void
  downloadingIds: Set<string>
  showPreview?: boolean
  refreshTrigger?: number
  groupByAuthor?: boolean
  onPendingCountChange?: (count: number) => void
  onDownloadAllRef?: React.MutableRefObject<(() => Promise<void>) | null>
}

export function RecentUpdates({
  onDownload,
  onDelete,
  downloadingIds,
  showPreview = false,
  refreshTrigger = 0,
  groupByAuthor = false,
  onPendingCountChange,
  onDownloadAllRef,
}: RecentUpdatesProps) {
  const { updates, isLoading, pendingUpdates, authorGroups, reload } = useRecentUpdates(refreshTrigger)

  // 通知父组件待下载数量变化
  useEffect(() => {
    if (onPendingCountChange) {
      onPendingCountChange(pendingUpdates.length)
    }
  }, [pendingUpdates.length, onPendingCountChange])

  // 暴露下载全部函数给父组件
  useEffect(() => {
    if (onDownloadAllRef) {
      onDownloadAllRef.current = async () => {
        if (pendingUpdates.length === 0) return
        for (const update of pendingUpdates) {
          await onDownload(update)
        }
      }
    }
  }, [pendingUpdates, onDownload, onDownloadAllRef])


  const handleDownloadAllForAuthor = async (mangas: MangaItem[]) => {
    for (const manga of mangas) {
      await onDownload(manga as RecentUpdate)
    }
  }

  // 按更新时间排序的更新列表（不按作者分类时使用）
  const sortedUpdates = useMemo(() => {
    return [...updates].sort((a, b) => {
      const dateA = a.updated_at ? new Date(a.updated_at).getTime() : 0
      const dateB = b.updated_at ? new Date(b.updated_at).getTime() : 0
      return dateB - dateA // 降序：最新的在前
    })
  }, [updates])

  // 按更新时间排序的作者组（按作者分类时使用）
  const sortedAuthorGroups = useMemo(() => {
    return authorGroups.map(ag => ({
      ...ag,
      mangas: [...ag.mangas].sort((a, b) => {
        const dateA = a.updated_at ? new Date(a.updated_at).getTime() : 0
        const dateB = b.updated_at ? new Date(b.updated_at).getTime() : 0
        return dateB - dateA // 降序：最新的在前
      })
    })).sort((a, b) => {
      // 作者组也按最新更新时间排序
      const latestA = a.mangas[0]?.updated_at ? new Date(a.mangas[0].updated_at).getTime() : 0
      const latestB = b.mangas[0]?.updated_at ? new Date(b.mangas[0].updated_at).getTime() : 0
      return latestB - latestA // 降序：最新的在前
    })
  }, [authorGroups])

  if (updates.length === 0) {
    return (
      <div className="glass rounded-lg overflow-hidden">
        <div className="glass-muted p-6 bg-gradient-to-r from-primary/10 via-primary/5 to-transparent">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary" />
            <h2 className="text-2xl font-bold">收藏作者最近更新</h2>
          </div>
        </div>
        <div className="p-6">
          <p className="text-muted-foreground text-center py-8">暂无收藏作者的更新</p>
        </div>
      </div>
    )
  }

  return (
    <div className="glass rounded-lg overflow-hidden">
      <div className="glass-muted p-6 bg-gradient-to-r from-primary/10 via-primary/5 to-transparent">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-primary" />
          <h2 className="text-2xl font-bold">收藏作者最近更新</h2>
          <span className="text-sm text-muted-foreground glass-muted px-3 py-1 rounded-full">
            {updates.length - pendingUpdates.length}/{updates.length} 已下载
          </span>
        </div>
      </div>

      <div className="p-6">
        {groupByAuthor ? (
          <div className="space-y-6">
            {sortedAuthorGroups.map((authorGroup) => (
              <AuthorSection
                key={authorGroup.author}
                authorGroup={authorGroup}
                onDownload={(manga: MangaItem) => onDownload(manga as RecentUpdate)}
                onDownloadAll={handleDownloadAllForAuthor}
                onDelete={(manga: MangaItem) => onDelete(manga as RecentUpdate)}
                downloadingIds={downloadingIds}
                showPreview={showPreview}
                selectionMode={false}
                selectedIds={new Set()}
                onToggleSelect={undefined}
              />
            ))}
          </div>
        ) : (
          <div
            className={`grid gap-3 ${
              showPreview
                ? "grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5"
                : "grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 2xl:grid-cols-10"
            }`}
          >
            {sortedUpdates.map((update) => (
              <MangaCard
                key={update.id}
                manga={update}
                onDownload={(manga: MangaItem) => onDownload(manga as RecentUpdate)}
                onDelete={(manga: MangaItem) => onDelete(manga as RecentUpdate)}
                isDownloading={downloadingIds.has(update.id)}
                showPreview={showPreview}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
