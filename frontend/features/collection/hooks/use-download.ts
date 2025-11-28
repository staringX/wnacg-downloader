// 下载功能相关的 hooks
"use client"

import { useState, useEffect } from "react"
import { downloadApi, recentUpdatesApi } from "@/lib/api"
import { useRunningTasks } from "@/hooks/use-task-status"
import { useToast } from "@/hooks/use-toast"
import type { MangaItem, RecentUpdate } from "@/lib/types"

export function useDownload() {
  const [downloadingIds, setDownloadingIds] = useState<Set<string>>(new Set())
  const [taskIds, setTaskIds] = useState<Map<string, string>>(new Map())
  const { toast } = useToast()
  const { tasks: runningDownloadTasks } = useRunningTasks("download")

  // 根据运行中的任务更新downloadingIds
  useEffect(() => {
    const downloadingSet = new Set<string>()
    runningDownloadTasks.forEach((task) => {
      if (task.manga_id && (task.status === "running" || task.status === "pending")) {
        downloadingSet.add(task.manga_id)
        setTaskIds((prev) => new Map(prev).set(task.manga_id!, task.id))
      }
    })
    setDownloadingIds(downloadingSet)
  }, [runningDownloadTasks])

  const handleDownload = async (manga: MangaItem | RecentUpdate) => {
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
      // 判断是RecentUpdate还是Manga
      // RecentUpdate从最近更新下载，需要使用不同的API
      // 注意：RecentUpdate的ID是RecentUpdate表的ID，不是Manga表的ID
      // 我们通过检查manga是否有is_downloaded字段且is_favorited为false来判断
      // 但实际上，从RecentUpdates组件调用的都是RecentUpdate
      // 为了简化，我们假设如果is_favorited为false或undefined，且is_downloaded为false，可能是RecentUpdate
      // 但更可靠的方法是：在RecentUpdates组件中直接使用downloadFromUpdate API
      // 这里我们暂时使用一个简单的判断：如果manga有is_downloaded字段，且为false，且is_favorited为false或undefined，则可能是RecentUpdate
      // 但实际上，由于RecentUpdates组件已经直接调用了downloadFromUpdate，这里应该不会走到RecentUpdate的分支
      // 为了安全，我们默认使用downloadManga API，除非明确知道是RecentUpdate
      
      // 由于RecentUpdates组件已经直接使用downloadFromUpdate，这里应该都是Manga
      const response = await downloadApi.downloadManga(manga.id)

      if (response.success && response.data) {
        const taskId = response.data.task_id
        if (taskId) {
          setTaskIds((prev) => new Map(prev).set(manga.id, taskId))
          setDownloadingIds((prev) => new Set(prev).add(manga.id))

          toast({
            title: "下载已开始",
            description: `开始下载: ${manga.title}`,
          })
        } else {
          toast({
            title: "下载完成",
            description: manga.title + " 已下载",
          })
        }
      } else {
        throw new Error(response.error || "下载失败")
      }
    } catch (error) {
      console.error("Download error:", error)
      toast({
        title: "下载失败",
        description: error instanceof Error ? error.message : "请稍后重试",
        variant: "destructive",
      })
    }
  }

  const handleDownloadAll = async (mangas: MangaItem[]) => {
    const ids = mangas.map((m) => m.id)
    setDownloadingIds((prev) => new Set([...prev, ...ids]))

    try {
      const response = await downloadApi.downloadBatch(ids)

      if (response.success) {
        toast({
          title: "批量下载完成",
          description: `成功下载 ${mangas.length} 个漫画`,
        })
      } else {
        throw new Error(response.error || "批量下载失败")
      }
    } catch (error) {
      console.error("Batch download error:", error)
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

  // 监听下载任务完成
  useEffect(() => {
    runningDownloadTasks.forEach((task) => {
      if (task.status === "completed" && task.manga_id) {
        setDownloadingIds((prev) => {
          const next = new Set(prev)
          next.delete(task.manga_id!)
          return next
        })
        toast({
          title: "下载完成",
          description: task.message || "下载成功",
        })
      } else if (task.status === "failed" && task.manga_id) {
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

  return {
    downloadingIds,
    handleDownload,
    handleDownloadAll,
  }
}

