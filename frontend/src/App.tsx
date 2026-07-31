import { useCallback, useState } from "react"
import { Header } from "@/components/layout/header"
import type { TabKey } from "@/components/layout/header"
import { SyncProgressStrip } from "@/components/layout/sync-progress-strip"
import { MobileMenu } from "@/components/layout/mobile-menu"
import { SyncFab } from "@/components/layout/sync-fab"
import { CollectionView } from "@/features/collection/collection-view"
import { RecentView } from "@/features/recent-updates/recent-view"
import { SettingsDialog } from "@/features/settings/settings-dialog"
import { useAppData } from "@/hooks/use-app-data"
import { useDownloads } from "@/hooks/use-downloads"
import { useSync } from "@/hooks/use-sync"
import { useIsMobile } from "@/hooks/use-mobile"
import { useToast } from "@/components/common/toast-context"
import { mangaApi, downloadApi, recentUpdatesApi } from "@/lib/api"
import { openOriginalSite } from "@/lib/komga"
import type { MangaItem, RecentUpdate } from "@/lib/types"

const PREVIEW_KEY = "mangavault-show-preview"

export function App() {
  const { toast } = useToast()
  const isMobile = useIsMobile()

  const {
    mangas,
    recentUpdates,
    settings,
    setSettings,
    refetchMangas,
    refetchUpdates,
    refetchSettings,
    removeManga,
    removeMangas,
  } = useAppData()

  const [tab, setTab] = useState<TabKey>("collection")
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [showPreview, setShowPreview] = useState<boolean>(() => {
    const v = window.localStorage.getItem(PREVIEW_KEY)
    return v === null ? true : v === "true"
  })

  const handleShowPreviewChange = (v: boolean) => {
    setShowPreview(v)
    window.localStorage.setItem(PREVIEW_KEY, String(v))
  }

  const { byManga: downloads } = useDownloads(refetchMangas)

  // 同期完了時は一覧に加えて設定（最后更新時刻）も再取得する
  const onCollectionDone = useCallback(() => {
    refetchMangas()
    refetchSettings()
  }, [refetchMangas, refetchSettings])
  const onRecentDone = useCallback(() => {
    refetchUpdates()
    refetchSettings()
  }, [refetchUpdates, refetchSettings])

  const { strip, syncCollection, syncRecent, isCollectionSyncing, isRecentSyncing } = useSync({
    onCollectionDone,
    onRecentDone,
  })

  // 相互排他フラグ：更新中は他の更新もダウンロードも不可／ダウンロード中は更新不可
  const isSyncing = isCollectionSyncing || isRecentSyncing
  const isDownloading = Object.keys(downloads).length > 0
  const syncDisabled = isSyncing || isDownloading
  const downloadDisabled = isSyncing

  // —— 收藏夹操作 ——
  const handleDownload = useCallback(
    async (id: string) => {
      const res = await downloadApi.downloadManga(id)
      if (res.success) toast("已加入下载队列")
      else toast(res.error || "无法开始下载")
    },
    [toast]
  )

  const handleDelete = useCallback(
    async (id: string) => {
      removeManga(id)
      const res = await mangaApi.deleteManga(id)
      if (res.success) toast("已删除")
      else {
        toast(res.error || "删除失败")
        refetchMangas()
      }
    },
    [removeManga, refetchMangas, toast]
  )

  const handleBatchDelete = useCallback(
    async (ids: string[]) => {
      if (ids.length === 0) return
      removeMangas(ids)
      await Promise.all(ids.map((id) => mangaApi.deleteManga(id)))
      toast(`已删除 ${ids.length} 项`)
      refetchMangas()
    },
    [removeMangas, refetchMangas, toast]
  )

  const handleDownloadAll = useCallback(
    async (ids: string[]) => {
      if (ids.length === 0) return
      const res = await downloadApi.downloadBatch(ids)
      if (res.success) toast(`已加入下载队列 · ${ids.length} 部`)
      else toast(res.error || "批量下载失败")
    },
    [toast]
  )

  const handleOpenOriginal = useCallback((m: MangaItem) => {
    openOriginalSite(m.manga_url)
  }, [])

  // —— 最近更新操作 ——
  const handleRecentDownload = useCallback(
    async (id: string) => {
      const res = await recentUpdatesApi.downloadFromUpdate(id)
      if (res.success) {
        toast("已加入下载队列")
        refetchUpdates()
      } else {
        toast(res.error || "无法开始下载")
      }
    },
    [refetchUpdates, toast]
  )

  const handleToggleFavorite = useCallback(
    async (u: RecentUpdate) => {
      if (u.is_favorited) return // 已收藏，不重复请求
      const res = await recentUpdatesApi.addUpdateToFavorite(u.id)
      if (res.success) {
        toast(res.data?.message || "已收藏到网站")
        refetchUpdates()
      } else {
        toast(res.error || "收藏失败")
      }
    },
    [refetchUpdates, toast]
  )

  return (
    <div style={{ minHeight: "100%", display: "flex", flexDirection: "column" }}>
      <Header
        currentTab={tab}
        onTabChange={setTab}
        updatesCount={recentUpdates.length}
        isMobile={isMobile}
        onOpenSettings={() => setSettingsOpen(true)}
        onToggleMobileMenu={() => setMobileMenuOpen((v) => !v)}
      />

      <SyncProgressStrip strip={strip} />

      <MobileMenu
        open={isMobile && mobileMenuOpen}
        onClose={() => setMobileMenuOpen(false)}
        currentTab={tab}
        onTabChange={setTab}
        updatesCount={recentUpdates.length}
        onOpenSettings={() => setSettingsOpen(true)}
      />

      <main
        style={{
          flex: 1,
          width: "100%",
          maxWidth: 1480,
          margin: "0 auto",
          padding: "clamp(16px, 3vw, 30px) clamp(14px, 3vw, 28px) 120px",
        }}
      >
        {tab === "collection" ? (
          <CollectionView
            mangas={mangas}
            downloads={downloads}
            showPreview={showPreview}
            isSyncing={isCollectionSyncing}
            syncDisabled={syncDisabled}
            downloadDisabled={downloadDisabled}
            syncedAt={settings.collection_synced_at}
            onSync={syncCollection}
            onDownload={handleDownload}
            onDelete={handleDelete}
            onBatchDelete={handleBatchDelete}
            onDownloadAll={handleDownloadAll}
            onOpenOriginal={handleOpenOriginal}
          />
        ) : (
          <RecentView
            updates={recentUpdates}
            downloads={downloads}
            showPreview={showPreview}
            isSyncing={isRecentSyncing}
            syncDisabled={syncDisabled}
            downloadDisabled={downloadDisabled}
            syncedAt={settings.recent_synced_at}
            onSync={syncRecent}
            onDownload={handleRecentDownload}
            onToggleFavorite={handleToggleFavorite}
            onOpenOriginal={(u) => openOriginalSite(u.manga_url)}
          />
        )}
      </main>

      {isMobile && (
        <SyncFab onSync={syncCollection} syncing={isCollectionSyncing || isRecentSyncing} />
      )}

      <SettingsDialog
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
        config={settings}
        onSaved={(cfg) => setSettings(cfg)}
        showPreview={showPreview}
        onShowPreviewChange={handleShowPreviewChange}
        onDownloadStatusUpdated={refetchMangas}
        onRecentUpdatesCleared={refetchUpdates}
      />
    </div>
  )
}
