// 主页面
"use client"

import { useState, useMemo } from "react"
import { Header } from "@/components/layout/header"
import { AppTabs } from "@/components/layout/tabs"
import { AuthorSection } from "@/features/collection/components/author-section"
import { RecentUpdates } from "@/features/recent-updates/components/recent-updates"
import { useCollection } from "@/features/collection/hooks/use-collection"
import { useDownload } from "@/features/collection/hooks/use-download"
import { useSelection } from "@/features/collection/hooks/use-selection"
import { useDelete } from "@/features/collection/hooks/use-delete"
import type { MangaItem, RecentUpdate } from "@/lib/types"

export default function HomePage() {
  const [showPreview, setShowPreview] = useState(false)
  const [recentUpdatesKey, setRecentUpdatesKey] = useState(0)

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

  const handleDownloadAllPending = async () => {
    const allPending = authorGroups.flatMap(ag =>
      ag.mangas.filter(m => !m.downloaded_at && !m.is_downloaded)
    )
    await handleDownloadAll(allPending)
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
      />

      <main className="container mx-auto px-4 py-6">
        <AppTabs
          collectionContent={
            isLoading ? (
              <div className="text-center py-12 text-muted-foreground">加载中...</div>
            ) : authorGroups.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-muted-foreground mb-4">还没有漫画数据，请点击"同步收藏夹"按钮</p>
              </div>
            ) : (
              <div className="space-y-6">
                {authorGroups.map(authorGroup => (
                  <AuthorSection
                    key={authorGroup.author}
                    authorGroup={authorGroup}
                    onDownload={handleDownloadManga}
                    onDownloadAll={handleDownloadAll}
                    onDelete={handleDeleteManga}
                    downloadingIds={downloadingIds}
                    showPreview={showPreview}
                    selectionMode={selectionMode}
                    selectedIds={selectedIds}
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
              downloadingIds={downloadingIds}
              showPreview={showPreview}
            />
          }
          onTabChange={value => {
            if (value === "updates") {
              setRecentUpdatesKey(prev => prev + 1)
            }
          }}
        />
      </main>
    </div>
  )
}
