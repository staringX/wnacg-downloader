"use client"

import { useState, useEffect, useMemo } from "react"
import { AuthorSection } from "@/components/author-section"
import { RecentUpdates } from "@/components/recent-updates"
import { SyncButton } from "@/components/sync-button"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Download, Library, Sparkles, ImageIcon, CheckCircle2, X } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import type { AuthorGroup, MangaItem } from "@/lib/types"
import { api } from "@/lib/api"
import { mockAllMangas } from "@/lib/mock-data"
import { useRunningTasks } from "@/hooks/use-task-status"

export default function HomePage() {
  const [authorGroups, setAuthorGroups] = useState<AuthorGroup[]>([])
  const [downloadingIds, setDownloadingIds] = useState<Set<string>>(new Set())
  const [taskIds, setTaskIds] = useState<Map<string, string>>(new Map()) // manga_id -> task_id
  const [isLoading, setIsLoading] = useState(true)
  const [showPreview, setShowPreview] = useState(false)
  const [selectionMode, setSelectionMode] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [recentUpdatesKey, setRecentUpdatesKey] = useState(0) // 用于强制重新渲染RecentUpdates组件
  const { toast } = useToast()
  
  // 获取正在运行的下载任务
  const { tasks: runningDownloadTasks } = useRunningTasks("download")
  
  // 根据运行中的任务更新downloadingIds
  useEffect(() => {
    const downloadingSet = new Set<string>()
    runningDownloadTasks.forEach((task) => {
      if (task.manga_id && (task.status === "running" || task.status === "pending")) {
        downloadingSet.add(task.manga_id)
        // 保存任务ID映射
        setTaskIds((prev) => new Map(prev).set(task.manga_id!, task.id))
      }
    })
    setDownloadingIds(downloadingSet)
  }, [runningDownloadTasks])

  const loadMangas = async () => {
    setIsLoading(true)
    try {
      const response = await api.fetchMangas()
      let mangas: MangaItem[]

      if (response.success && response.data) {
        mangas = response.data
      } else {
        // Fallback to mock data if API fails
        mangas = mockAllMangas
      }

      const grouped = mangas.reduce((acc: AuthorGroup[], manga: MangaItem) => {
        let authorGroup = acc.find((g) => g.author === manga.author)
        if (!authorGroup) {
          authorGroup = { author: manga.author, mangas: [] }
          acc.push(authorGroup)
        }
        authorGroup.mangas.push(manga)
        return acc
      }, [])

      setAuthorGroups(grouped)
    } catch (error) {
      console.error("[v0] Load error:", error)
      // Fallback to mock data
      const mangas = mockAllMangas
      const grouped = mangas.reduce((acc: AuthorGroup[], manga: MangaItem) => {
        let authorGroup = acc.find((g) => g.author === manga.author)
        if (!authorGroup) {
          authorGroup = { author: manga.author, mangas: [] }
          acc.push(authorGroup)
        }
        authorGroup.mangas.push(manga)
        return acc
      }, [])
      setAuthorGroups(grouped)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadMangas()
  }, [])

  const handleDownload = async (manga: MangaItem) => {
    // 检查是否已有正在运行的下载任务
    if (downloadingIds.has(manga.id)) {
      toast({
        title: "下载进行中",
        description: "该漫画正在下载中，请等待完成",
        variant: "default",
      })
      return
    }

    try {
      const response = await api.downloadManga(manga.id)

      if (response.success && response.data) {
        const taskId = response.data.task_id
        if (taskId) {
          // 保存任务ID映射
          setTaskIds((prev) => new Map(prev).set(manga.id, taskId))
          // 添加到下载中列表
          setDownloadingIds((prev) => new Set(prev).add(manga.id))
          
          toast({
            title: "下载已开始",
            description: `开始下载: ${manga.title}`,
          })
        } else {
          // 如果返回空taskId，说明已经下载完成
          toast({
            title: "下载完成",
            description: manga.title + " 已下载",
          })
          // 刷新数据
          loadMangas()
        }
      } else {
        throw new Error(response.error || "下载失败")
      }
    } catch (error) {
      console.error("[v0] Download error:", error)
      toast({
        title: "下载失败",
        description: error instanceof Error ? error.message : "请稍后重试",
        variant: "destructive",
      })
    }
  }
  
  // 监听下载任务完成
  useEffect(() => {
    runningDownloadTasks.forEach((task) => {
      if (task.status === "completed" && task.manga_id) {
        // 从下载中列表移除
        setDownloadingIds((prev) => {
          const next = new Set(prev)
          next.delete(task.manga_id!)
          return next
        })
        // 刷新数据
        loadMangas()
        toast({
          title: "下载完成",
          description: task.message || "下载成功",
        })
      } else if (task.status === "failed" && task.manga_id) {
        // 从下载中列表移除
        setDownloadingIds((prev) => {
          const next = new Set(prev)
          next.delete(task.manga_id!)
          return next
        })
        toast({
          title: "下载失败",
          description: task.error_message || "下载过程中出现错误",
          variant: "destructive",
        })
      }
    })
  }, [runningDownloadTasks, toast])

  const handleDownloadAll = async (mangas: MangaItem[]) => {
    const ids = mangas.map((m) => m.id)
    setDownloadingIds((prev) => new Set([...prev, ...ids]))

    try {
      const response = await api.downloadBatch(ids)

      if (response.success) {
        toast({
          title: "批量下载完成",
          description: `成功下载 ${mangas.length} 个漫画`,
        })

        setAuthorGroups((prev) =>
          prev.map((ag) => ({
            ...ag,
            mangas: ag.mangas.map((m) => (ids.includes(m.id) ? { ...m, downloaded_at: new Date().toISOString() } : m)),
          })),
        )
      } else {
        throw new Error(response.error || "批量下载失败")
      }
    } catch (error) {
      console.error("[v0] Batch download error:", error)
      toast({
        title: "批量下载失败",
        description: error instanceof Error ? error.message : "请稍后重试",
        variant: "destructive",
      })
    } finally {
      setDownloadingIds((prev) => {
        const next = new Set(prev)
        ids.forEach((id) => next.delete(id))
        return next
      })
    }
  }

  const handleDownloadAllPending = async () => {
    const allPending = authorGroups.flatMap((ag) => ag.mangas.filter((m) => !m.downloaded_at && !m.is_downloaded))

    if (allPending.length === 0) {
      toast({
        title: "没有待下载的漫画",
        description: "所有漫画都已下载",
      })
      return
    }

    await handleDownloadAll(allPending)
  }

  const handleDelete = async (manga: MangaItem) => {
    try {
      const response = await api.deleteManga(manga.id)

      if (response.success) {
        toast({
          title: "删除成功",
          description: manga.title,
        })

        // Remove manga from state
        setAuthorGroups(
          (prev) =>
            prev
              .map((ag) => ({
                ...ag,
                mangas: ag.mangas.filter((m) => m.id !== manga.id),
              }))
              .filter((ag) => ag.mangas.length > 0), // Remove empty author groups
        )
      } else {
        throw new Error(response.error || "删除失败")
      }
    } catch (error) {
      console.error("[v0] Delete error:", error)
      toast({
        title: "删除失败",
        description: error instanceof Error ? error.message : "请稍后重试",
        variant: "destructive",
      })
    }
  }

  const handleToggleSelect = (manga: MangaItem) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(manga.id)) {
        next.delete(manga.id)
      } else {
        next.add(manga.id)
      }
      return next
    })
  }

  const handleBatchDelete = async () => {
    if (selectedIds.size === 0) {
      toast({
        title: "请先选择要删除的漫画",
        description: "点击漫画卡片进行选择",
      })
      return
    }

    const selectedMangas = authorGroups.flatMap((ag) => ag.mangas).filter((m) => selectedIds.has(m.id))

    if (confirm(`确定要删除选中的 ${selectedIds.size} 个漫画吗？此操作无法撤销。`)) {
      try {
        // Delete all selected mangas
        await Promise.all(Array.from(selectedIds).map((id) => api.deleteManga(id)))

        toast({
          title: "批量删除成功",
          description: `已删除 ${selectedIds.size} 个漫画`,
        })

        // Remove deleted mangas from state
        setAuthorGroups((prev) =>
          prev
            .map((ag) => ({
              ...ag,
              mangas: ag.mangas.filter((m) => !selectedIds.has(m.id)),
            }))
            .filter((ag) => ag.mangas.length > 0),
        )

        // Clear selection
        setSelectedIds(new Set())
        setSelectionMode(false)
      } catch (error) {
        console.error("[v0] Batch delete error:", error)
        toast({
          title: "批量删除失败",
          description: error instanceof Error ? error.message : "请稍后重试",
          variant: "destructive",
        })
      }
    }
  }

  const handleToggleSelectionMode = () => {
    setSelectionMode((prev) => !prev)
    setSelectedIds(new Set()) // Clear selection when toggling mode
  }

  const totalMangas = authorGroups.reduce((sum, ag) => sum + ag.mangas.length, 0)

  const downloadedMangas = authorGroups.reduce(
    (sum, ag) => sum + ag.mangas.filter((m) => m.downloaded_at || m.is_downloaded).length,
    0,
  )

  const pendingMangas = totalMangas - downloadedMangas

  return (
    <div className="min-h-screen">
      <header className="glass-header sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-balance bg-gradient-to-r from-primary via-primary/80 to-primary/60 bg-clip-text text-transparent">
                漫画下载管理器
              </h1>
              <p className="text-sm text-muted-foreground mt-1">
                总计: {totalMangas} | 已下载: {downloadedMangas} | 待下载: {pendingMangas}
              </p>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 glass-card px-3 py-2 rounded-lg">
                <ImageIcon className="w-4 h-4 text-muted-foreground" />
                <Label htmlFor="preview-toggle" className="text-sm cursor-pointer">
                  预览图
                </Label>
                <Switch id="preview-toggle" checked={showPreview} onCheckedChange={setShowPreview} />
              </div>

              <Button
                onClick={handleToggleSelectionMode}
                variant={selectionMode ? "default" : "outline"}
                className={
                  selectionMode ? "bg-primary text-primary-foreground" : "glass-card bg-transparent hover:bg-primary/10"
                }
              >
                <CheckCircle2 className="w-4 h-4 mr-2" />
                {selectionMode ? "退出多选" : "多选模式"}
              </Button>

              {selectionMode && selectedIds.size > 0 && (
                <Button
                  onClick={handleBatchDelete}
                  className="bg-red-500 text-white hover:bg-red-600 hover:scale-105 active:scale-95 transition-all duration-200 shadow-lg"
                >
                  <X className="w-4 h-4 mr-2" />
                  删除选中 ({selectedIds.size})
                </Button>
              )}

              <SyncButton onSyncComplete={loadMangas} />
              {!selectionMode && pendingMangas > 0 && (
                <Button
                  onClick={handleDownloadAllPending}
                  className="bg-primary text-primary-foreground hover:bg-primary/90 hover:scale-105 active:scale-95 transition-all duration-200 shadow-lg"
                >
                  <Download className="w-4 h-4 mr-2" />
                  下载全部待下载 ({pendingMangas})
                </Button>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6">
        <Tabs defaultValue="collection" className="w-full" onValueChange={(value) => {
          // 当切换到"最近更新"标签页时，触发数据获取
          if (value === "updates") {
            // 通过更新key强制重新渲染RecentUpdates组件，触发useEffect
            setRecentUpdatesKey(prev => prev + 1)
          }
        }}>
          <TabsList className="mb-6 glass">
            <TabsTrigger value="collection" className="gap-2">
              <Library className="w-4 h-4" />
              我的收藏
            </TabsTrigger>
            <TabsTrigger value="updates" className="gap-2">
              <Sparkles className="w-4 h-4" />
              最近更新
            </TabsTrigger>
          </TabsList>

          <TabsContent value="collection">
            {isLoading ? (
              <div className="text-center py-12 text-muted-foreground">加载中...</div>
            ) : authorGroups.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-muted-foreground mb-4">还没有漫画数据，请点击"同步收藏夹"按钮</p>
              </div>
            ) : (
              <div className="space-y-6">
                {authorGroups.map((authorGroup) => (
                  <AuthorSection
                    key={authorGroup.author}
                    authorGroup={authorGroup}
                    onDownload={handleDownload}
                    onDownloadAll={handleDownloadAll}
                    onDelete={handleDelete}
                    downloadingIds={downloadingIds}
                    showPreview={showPreview}
                    selectionMode={selectionMode}
                    selectedIds={selectedIds}
                    onToggleSelect={handleToggleSelect}
                  />
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="updates">
            <RecentUpdates
              refreshTrigger={recentUpdatesKey}
              onDownload={handleDownload}
              onDelete={handleDelete}
              downloadingIds={downloadingIds}
              showPreview={showPreview}
            />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  )
}
