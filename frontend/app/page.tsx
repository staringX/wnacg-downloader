// 主页面
"use client"

import { useState, useMemo, useRef } from "react"
import { Header } from "@/components/layout/header"
import { AppTabs } from "@/components/layout/tabs"
import { AuthorSection } from "@/features/collection/components/author-section"
import { MangaCard } from "@/features/collection/components/manga-card"
import { RecentUpdates } from "@/features/recent-updates/components/recent-updates"
import { useCollection } from "@/features/collection/hooks/use-collection"
import { useDownload } from "@/features/collection/hooks/use-download"
import { useSelection } from "@/features/collection/hooks/use-selection"
import { useDelete } from "@/features/collection/hooks/use-delete"
import { useFavorite } from "@/features/collection/hooks/use-favorite"
import type { MangaItem, RecentUpdate } from "@/lib/types"

export default function HomePage() {
  const [showPreview, setShowPreview] = useState(false)
  const [recentUpdatesKey, setRecentUpdatesKey] = useState(0)
  const [currentTab, setCurrentTab] = useState<"collection" | "updates">("collection")
  const [groupByAuthor, setGroupByAuthor] = useState(false)

  const { authorGroups, isLoading, reload, setAuthorGroups } = useCollection()
  const { downloadingIds, handleDownload, handleDownloadAll } = useDownload()
  const {
    selectionMode,
    selectedIds,
    handleToggleSelect,
    handleToggleSelectionMode,
    clearSelection,
    setSelectedIds,
  } = useSelection()
  const { handleDelete, handleBatchDelete } = useDelete()
  const { handleFavorite } = useFavorite()

  const totalMangas = useMemo(
    () => authorGroups.reduce((sum, ag) => sum + ag.mangas.length, 0),
    [authorGroups]
  )

  const downloadedMangas = useMemo(
    () =>
      authorGroups.reduce(
        (sum, ag) => sum + ag.mangas.filter(m => m.downloaded_at || m.is_downloaded).length,
        0
      ),
    [authorGroups]
  )

  const pendingMangas = totalMangas - downloadedMangas

  // 按更新时间排序的漫画列表（不按作者分类时使用）
  const sortedMangas = useMemo(() => {
    const allMangas = authorGroups.flatMap(ag => ag.mangas)
    return [...allMangas].sort((a, b) => {
      const dateA = a.updated_at ? new Date(a.updated_at).getTime() : 0
      const dateB = b.updated_at ? new Date(b.updated_at).getTime() : 0
      return dateB - dateA // 降序：最新的在前
    })
  }, [authorGroups])

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

  const handleDownloadAllPending = async () => {
    const allPending = authorGroups.flatMap(ag =>
      ag.mangas.filter(m => !m.downloaded_at && !m.is_downloaded)
    )
    await handleDownloadAll(allPending)
  }

  // 最近更新的状态
  const [pendingUpdatesCount, setPendingUpdatesCount] = useState(0)
  const downloadAllUpdatesRef = useRef<(() => Promise<void>) | null>(null)

  // 最近更新的下载全部处理
  const handleDownloadAllUpdates = async () => {
    if (downloadAllUpdatesRef.current) {
      await downloadAllUpdatesRef.current()
    }
  }

  // 最近更新的同步处理
  const handleSyncRecentUpdates = () => {
    setRecentUpdatesKey(prev => prev + 1)
  }

  const handleDeleteManga = async (manga: MangaItem) => {
    await handleDelete(manga, authorGroups, setAuthorGroups)
  }

  const handleBatchDeleteMangas = async () => {
    await handleBatchDelete(selectedIds, authorGroups, setAuthorGroups, clearSelection)
  }

  const handleDownloadManga = async (manga: MangaItem | RecentUpdate) => {
    await handleDownload(manga)
    reload()
  }

  const handleFavoriteManga = async (manga: MangaItem) => {
    await handleFavorite(manga)
    reload()  // 重新加载数据以更新is_favorited状态
  }

  const handleDeleteRecentUpdate = async (manga: RecentUpdate) => {
    // 最近更新的删除逻辑可以在这里实现
    console.log("Delete recent update:", manga)
  }

  return (
    <div className="min-h-screen">
      <Header
        totalMangas={totalMangas}
        downloadedMangas={downloadedMangas}
        pendingMangas={pendingMangas}
        showPreview={showPreview}
        onPreviewChange={setShowPreview}
        selectionMode={selectionMode}
        onToggleSelectionMode={handleToggleSelectionMode}
        selectedCount={selectedIds.size}
        onBatchDelete={handleBatchDeleteMangas}
        onDownloadAllPending={handleDownloadAllPending}
        onSyncComplete={reload}
        currentTab={currentTab}
        groupByAuthor={groupByAuthor}
        onGroupByAuthorChange={setGroupByAuthor}
        onSyncRecentUpdates={handleSyncRecentUpdates}
        onDownloadAllUpdates={handleDownloadAllUpdates}
        pendingUpdatesCount={pendingUpdatesCount}
      />

      <main className="container mx-auto px-4 py-6">
        <AppTabs
          value={currentTab}
          collectionContent={
            isLoading ? (
              <div className="text-center py-12 text-muted-foreground">加载中...</div>
            ) : authorGroups.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-muted-foreground mb-4">还没有漫画数据，请点击"同步收藏夹"按钮</p>
              </div>
            ) : groupByAuthor ? (
              <div className="space-y-6">
                {sortedAuthorGroups.map(authorGroup => (
                  <AuthorSection
                    key={authorGroup.author}
                    authorGroup={authorGroup}
                    onDownload={handleDownloadManga}
                    onDownloadAll={handleDownloadAll}
                    onDelete={handleDeleteManga}
                    onFavorite={handleFavoriteManga}
                    downloadingIds={downloadingIds}
                    showPreview={showPreview}
                    selectionMode={selectionMode}
                    selectedIds={selectedIds}
                    onToggleSelect={handleToggleSelect}
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
                {sortedMangas.map(manga => (
                  <MangaCard
                    key={manga.id}
                    manga={manga}
                    onDownload={handleDownloadManga}
                    onDelete={handleDeleteManga}
                    onFavorite={handleFavoriteManga}
                    isDownloading={downloadingIds.has(manga.id)}
                    showPreview={showPreview}
                    selectionMode={selectionMode}
                    isSelected={selectedIds.has(manga.id)}
                    onToggleSelect={handleToggleSelect}
                  />
                ))}
              </div>
            )
          }
          updatesContent={
            <RecentUpdates
              refreshTrigger={recentUpdatesKey}
              onDownload={handleDownloadManga}
              onDelete={handleDeleteRecentUpdate}
              onFavorite={handleFavoriteManga}
              downloadingIds={downloadingIds}
              showPreview={showPreview}
              groupByAuthor={groupByAuthor}
              onPendingCountChange={setPendingUpdatesCount}
              onDownloadAllRef={downloadAllUpdatesRef}
            />
          }
          onTabChange={value => {
            setCurrentTab(value as "collection" | "updates")
            if (value === "updates") {
              setRecentUpdatesKey(prev => prev + 1)
            }
          }}
        />
      </main>
    </div>
  )
}
