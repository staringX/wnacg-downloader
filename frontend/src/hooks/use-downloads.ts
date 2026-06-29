import { useEffect, useMemo, useRef } from "react"
import { useRunningTasks } from "@/hooks/use-task-status"

export interface DownloadState {
  progress: number // 0-100
  status: string
}

// 通过 SSE 运行中任务列表，得出每个漫画的实时下载进度（DESIGN_SPEC §4.3）
export function useDownloads(onAnyComplete: () => void) {
  const { tasks } = useRunningTasks("download")
  const prevIdsRef = useRef<Set<string>>(new Set())

  const byManga = useMemo(() => {
    const map: Record<string, DownloadState> = {}
    for (const t of tasks) {
      if (t.manga_id && (t.status === "running" || t.status === "pending")) {
        map[t.manga_id] = { progress: t.progress ?? 0, status: t.status }
      }
    }
    return map
  }, [tasks])

  // 当某个下载任务从运行列表中消失（完成/失败），刷新收藏夹以更新状态
  useEffect(() => {
    const currentIds = new Set(
      tasks.filter((t) => t.manga_id).map((t) => t.manga_id as string)
    )
    const prev = prevIdsRef.current
    let disappeared = false
    for (const id of prev) {
      if (!currentIds.has(id)) {
        disappeared = true
        break
      }
    }
    prevIdsRef.current = currentIds
    if (disappeared) onAnyComplete()
  }, [tasks, onAnyComplete])

  return { byManga }
}
