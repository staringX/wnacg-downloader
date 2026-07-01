import { useCallback, useEffect, useState } from "react"
import { syncApi } from "@/lib/api"
import { useTaskStatus, useRunningTasks } from "@/hooks/use-task-status"
import { useToast } from "@/components/common/toast-context"

interface UseSyncArgs {
  onCollectionDone: () => void
  onRecentDone: () => void
}

export interface SyncStrip {
  active: boolean
  label: string
  progress: number
}

// 同步收藏夹 / 检索新作 的编排（DESIGN_SPEC §6.2）
export function useSync({ onCollectionDone, onRecentDone }: UseSyncArgs) {
  const { toast } = useToast()

  const [collectionTaskId, setCollectionTaskId] = useState<string | null>(null)
  const [recentTaskId, setRecentTaskId] = useState<string | null>(null)

  const { task: collectionTask } = useTaskStatus(collectionTaskId)
  const { task: recentTask } = useTaskStatus(recentTaskId)
  const { tasks: collectionRunning } = useRunningTasks("sync")
  const { tasks: recentRunning } = useRunningTasks("sync_recent_updates")

  // 页面恢复：接管正在运行的同步任务
  useEffect(() => {
    if (collectionRunning.length > 0 && !collectionTaskId) {
      setCollectionTaskId(collectionRunning[0].id)
    }
  }, [collectionRunning, collectionTaskId])

  useEffect(() => {
    if (recentRunning.length > 0 && !recentTaskId) {
      setRecentTaskId(recentRunning[0].id)
    }
  }, [recentRunning, recentTaskId])

  // 收藏夹同步完成监听
  useEffect(() => {
    if (!collectionTask) return
    if (collectionTask.status === "completed") {
      toast(collectionTask.message || "已同步收藏夹")
      onCollectionDone()
      const t = setTimeout(() => setCollectionTaskId(null), 500)
      return () => clearTimeout(t)
    }
    if (collectionTask.status === "failed") {
      toast(collectionTask.error_message || "同步失败")
      setCollectionTaskId(null)
    }
  }, [collectionTask, toast, onCollectionDone])

  // 最近更新同步完成监听
  useEffect(() => {
    if (!recentTask) return
    if (recentTask.status === "completed") {
      toast(recentTask.message || "已检索新作")
      onRecentDone()
      const t = setTimeout(() => setRecentTaskId(null), 500)
      return () => clearTimeout(t)
    }
    if (recentTask.status === "failed") {
      toast(recentTask.error_message || "检索失败")
      setRecentTaskId(null)
    }
  }, [recentTask, toast, onRecentDone])

  const syncCollection = useCallback(async () => {
    if (collectionTaskId) return
    const res = await syncApi.syncCollection()
    if (res.success && res.data) {
      setCollectionTaskId(res.data.task_id)
    } else {
      toast(res.error || "无法启动同步")
    }
  }, [collectionTaskId, toast])

  const syncRecent = useCallback(async () => {
    if (recentTaskId) return
    const res = await syncApi.syncRecentUpdates()
    if (res.success && res.data) {
      setRecentTaskId(res.data.task_id)
    } else {
      toast(res.error || "无法启动检索")
    }
  }, [recentTaskId, toast])

  // 进度条状态：优先显示当前活动的同步
  const activeTask = collectionTask ?? recentTask
  const strip: SyncStrip = {
    active: Boolean(collectionTaskId || recentTaskId),
    label: collectionTaskId ? "正在同步收藏夹…" : recentTaskId ? "正在检索新作…" : "",
    progress: activeTask?.progress ?? 0,
  }

  return {
    strip,
    syncCollection,
    syncRecent,
    isCollectionSyncing: Boolean(collectionTaskId),
    isRecentSyncing: Boolean(recentTaskId),
  }
}
