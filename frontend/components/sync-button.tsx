"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { RefreshCw } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { api } from "@/lib/api"
import { useTaskStatus, useRunningTasks } from "@/hooks/use-task-status"

interface SyncButtonProps {
  onSyncComplete?: () => void
}

export function SyncButton({ onSyncComplete }: SyncButtonProps) {
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null)
  const { task, isLoading: isTaskLoading } = useTaskStatus(currentTaskId)
  const { tasks: runningTasks } = useRunningTasks("sync")
  const { toast } = useToast()

  // 检查是否有正在运行的同步任务
  useEffect(() => {
    if (runningTasks.length > 0 && !currentTaskId) {
      // 如果有正在运行的任务，使用最新的任务ID
      setCurrentTaskId(runningTasks[0].id)
    }
  }, [runningTasks, currentTaskId])

  // 监听任务状态变化
  useEffect(() => {
    if (!task) return

    if (task.status === "completed") {
      toast({
        title: "同步完成",
        description: task.message || "已同步收藏夹数据",
      })
      onSyncComplete?.()
      setCurrentTaskId(null) // 清除任务ID
    } else if (task.status === "failed") {
      toast({
        title: "同步失败",
        description: task.error_message || "同步过程中出现错误",
        variant: "destructive",
      })
      setCurrentTaskId(null) // 清除任务ID
    }
  }, [task, toast, onSyncComplete])

  const isSyncing = task?.status === "running" || task?.status === "pending" || isTaskLoading
  const hasRunningTask = runningTasks.length > 0

  const handleSync = async () => {
    // 如果已有正在运行的任务，不允许重复创建
    if (hasRunningTask) {
      toast({
        title: "同步进行中",
        description: "已有同步任务正在运行，请等待完成",
        variant: "default",
      })
      return
    }

    try {
      const response = await api.syncCollection()

      if (response.success && response.data) {
        const taskId = response.data.task_id
        setCurrentTaskId(taskId)
        toast({
          title: "同步已开始",
          description: "同步任务已创建，正在后台执行...",
        })
      } else {
        throw new Error(response.error || "同步失败")
      }
    } catch (error) {
      console.error("[v0] Sync error:", error)
      toast({
        title: "同步失败",
        description: error instanceof Error ? error.message : "请稍后重试",
        variant: "destructive",
      })
    }
  }

  // 显示进度信息
  const progressText = task?.progress
    ? ` (${task.progress}%)`
    : task?.message
    ? ` - ${task.message}`
    : ""

  return (
    <Button
      onClick={handleSync}
      disabled={isSyncing || hasRunningTask}
      variant="outline"
      className="glass-card hover:shadow-lg transition-all bg-transparent"
    >
      <RefreshCw className={`w-4 h-4 mr-2 ${isSyncing ? "animate-spin" : ""}`} />
      {isSyncing ? `同步中...${progressText}` : "同步收藏夹"}
    </Button>
  )
}
