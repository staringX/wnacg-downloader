// 最近更新组件
"use client"

import { useState, useEffect } from "react"
import { MangaCard } from "@/features/collection/components/manga-card"
import { AuthorSection } from "@/features/collection/components/author-section"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Download, Sparkles, RefreshCw, Users } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import type { RecentUpdate, AuthorGroup, MangaItem } from "@/lib/types"
import { syncApi } from "@/lib/api"
import { useRecentUpdates } from "../hooks/use-recent-updates"
import { useTaskStatus, useRunningTasks } from "@/hooks/use-task-status"

interface RecentUpdatesProps {
  onDownload: (manga: RecentUpdate) => void
  onDelete: (manga: RecentUpdate) => void
  downloadingIds: Set<string>
  showPreview?: boolean
  refreshTrigger?: number
}

export function RecentUpdates({
  onDownload,
  onDelete,
  downloadingIds,
  showPreview = false,
  refreshTrigger = 0,
}: RecentUpdatesProps) {
  const [groupByAuthor, setGroupByAuthor] = useState(false)
  const { toast } = useToast()
  const { updates, isLoading, pendingUpdates, authorGroups, reload } = useRecentUpdates(refreshTrigger)

  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null)
  const { task, isLoading: isTaskLoading } = useTaskStatus(currentTaskId)
  const { tasks: runningTasks } = useRunningTasks("sync_recent_updates")

  // 检查是否有正在运行的同步最近更新任务
  useEffect(() => {
    if (runningTasks.length > 0 && !currentTaskId) {
      setCurrentTaskId(runningTasks[0].id)
    }
  }, [runningTasks, currentTaskId])

  // 监听任务状态变化
  useEffect(() => {
    if (!task) return

    if (task.status === "completed") {
      toast({
        title: "同步完成",
        description: task.message || "已同步最近更新",
      })
      reload()
      setCurrentTaskId(null)
    } else if (task.status === "failed") {
      toast({
        title: "同步失败",
        description: task.error_message || "同步过程中出现错误",
        variant: "destructive",
      })
      setCurrentTaskId(null)
    }
  }, [task, toast, reload])

  const isSyncing = task?.status === "running" || task?.status === "pending" || isTaskLoading
  const hasRunningTask = runningTasks.length > 0

  const handleRefresh = async () => {
    if (hasRunningTask) {
      toast({
        title: "同步进行中",
        description: "已有同步任务正在运行，请等待完成",
        variant: "default",
      })
      return
    }

    try {
      const syncResponse = await syncApi.syncRecentUpdates()
      if (!syncResponse.success) {
        toast({
          title: "同步失败",
          description: syncResponse.error || "同步最近更新失败",
          variant: "destructive",
        })
        return
      }

      if (syncResponse.data) {
        const taskId = syncResponse.data.task_id
        setCurrentTaskId(taskId)
        toast({
          title: "同步已开始",
          description: "同步任务已创建，正在后台执行...",
        })
      }
    } catch (error) {
      console.error("Refresh recent updates error:", error)
      toast({
        title: "更新失败",
        description: error instanceof Error ? error.message : "未知错误",
        variant: "destructive",
      })
    }
  }

  const progressText = task?.progress
    ? ` (${task.progress}%)`
    : task?.message
    ? ` - ${task.message}`
    : ""

  const handleDownloadAll = async () => {
    if (pendingUpdates.length === 0) return
    for (const update of pendingUpdates) {
      await onDownload(update)
    }
  }

  const handleDownloadAllForAuthor = async (mangas: MangaItem[]) => {
    for (const manga of mangas) {
      await onDownload(manga as RecentUpdate)
    }
  }

  if (updates.length === 0) {
    return (
      <div className="glass rounded-lg overflow-hidden">
        <div className="glass-muted p-6 bg-gradient-to-r from-primary/10 via-primary/5 to-transparent">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-primary" />
              <h2 className="text-2xl font-bold">收藏作者最近更新</h2>
            </div>

            <div className="flex items-center gap-3">
              <Button
                onClick={handleRefresh}
                variant="outline"
                size="sm"
                className="glass-card hover:shadow-lg transition-all bg-transparent"
                disabled={isSyncing || hasRunningTask}
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${isSyncing ? "animate-spin" : ""}`} />
                {isSyncing ? `同步中...${progressText}` : "同步最近更新"}
              </Button>
            </div>
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
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary" />
            <h2 className="text-2xl font-bold">收藏作者最近更新</h2>
            <span className="text-sm text-muted-foreground glass-muted px-3 py-1 rounded-full">
              {updates.length - pendingUpdates.length}/{updates.length} 已下载
            </span>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 glass-card px-3 py-2 rounded-lg">
              <Users className="w-4 h-4 text-muted-foreground" />
              <Label htmlFor="group-by-author-toggle" className="text-sm cursor-pointer">
                按作者分类
              </Label>
              <Switch
                id="group-by-author-toggle"
                checked={groupByAuthor}
                onCheckedChange={setGroupByAuthor}
              />
            </div>

            <Button
              onClick={handleRefresh}
              variant="outline"
              size="sm"
              className="glass-card hover:shadow-lg transition-all bg-transparent"
              disabled={isSyncing || hasRunningTask}
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${isSyncing ? "animate-spin" : ""}`} />
              {isSyncing ? `同步中...${progressText}` : "同步最近更新"}
            </Button>

            {pendingUpdates.length > 0 && (
              <Button
                onClick={handleDownloadAll}
                variant="default"
                className="bg-primary text-primary-foreground hover:bg-primary/90 shadow-lg hover:shadow-xl transition-all duration-300"
              >
                <Download className="w-4 h-4 mr-2" />
                下载全部新更新 ({pendingUpdates.length})
              </Button>
            )}
          </div>
        </div>
      </div>

      <div className="p-6">
        {groupByAuthor ? (
          <div className="space-y-6">
            {authorGroups.map((authorGroup) => (
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
            {updates.map((update) => (
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
