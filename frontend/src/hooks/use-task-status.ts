import { useState, useEffect, useCallback, useRef } from "react"
import type { TaskStatus } from "@/lib/types"

const API_BASE_URL = ""

export function useTaskStatus(taskId: string | null) {
  const [task, setTask] = useState<TaskStatus | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)
  const fallbackIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // 从数据库查询任务状态（用于页面刷新后恢复状态）
  const fetchTask = useCallback(async () => {
    if (!taskId) {
      setTask(null)
      return
    }

    setIsLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}`)
      if (response.ok) {
        const data = await response.json()
        setTask(data)
      } else {
        setTask(null)
      }
    } catch (error) {
      console.error("获取任务状态失败:", error)
      setTask(null)
    } finally {
      setIsLoading(false)
    }
  }, [taskId])

  // 初始化时查询任务状态
  useEffect(() => {
    fetchTask()
  }, [fetchTask])

  // 建立SSE连接监听任务状态更新
  useEffect(() => {
    if (!taskId) {
      return
    }

    const eventSource = new EventSource(`${API_BASE_URL}/api/events`)
    eventSourceRef.current = eventSource

    eventSource.addEventListener("task_created", (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.data?.task_id === taskId) {
          setTask((prev) => ({
            ...prev,
            id: data.data.task_id,
            task_type: data.data.task_type,
            status: data.data.status,
          } as TaskStatus))
        }
      } catch (error) {
        console.error("解析任务创建事件失败:", error)
      }
    })

    eventSource.addEventListener("task_updated", (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.data?.task_id === taskId) {
          setTask((prev) => ({
            ...prev,
            ...data.data,
          } as TaskStatus))
        }
      } catch (error) {
        console.error("解析任务更新事件失败:", error)
      }
    })

    eventSource.addEventListener("connected", () => {
      if (fallbackIntervalRef.current) {
        clearInterval(fallbackIntervalRef.current)
        fallbackIntervalRef.current = null
      }
    })

    eventSource.onerror = () => {
      if (eventSource.readyState === EventSource.CLOSED && !fallbackIntervalRef.current) {
        fallbackIntervalRef.current = setInterval(() => {
          fetchTask()
        }, 10000)
      }
    }

    return () => {
      if (fallbackIntervalRef.current) {
        clearInterval(fallbackIntervalRef.current)
        fallbackIntervalRef.current = null
      }
      eventSource.close()
      eventSourceRef.current = null
    }
  }, [taskId, fetchTask])

  return {
    task,
    isLoading,
    refetch: fetchTask,
  }
}

// 获取正在运行的任务列表（通过 SSE 推送刷新，断线时低频轮询兜底）
export function useRunningTasks(taskType?: string) {
  const [tasks, setTasks] = useState<TaskStatus[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)
  const fallbackIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchRunningTasks = useCallback(async () => {
    setIsLoading(true)
    try {
      const url = taskType
        ? `${API_BASE_URL}/api/tasks/running/list?task_type=${taskType}`
        : `${API_BASE_URL}/api/tasks/running/list`

      const response = await fetch(url)
      if (response.ok) {
        const data = await response.json()
        setTasks(data)
      }
    } catch (error) {
      console.error("获取运行中任务失败:", error)
    } finally {
      setIsLoading(false)
    }
  }, [taskType])

  useEffect(() => {
    fetchRunningTasks()
  }, [fetchRunningTasks])

  useEffect(() => {
    const eventSource = new EventSource(`${API_BASE_URL}/api/events`)
    eventSourceRef.current = eventSource

    const onTaskEvent = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data)
        if (data.data?.task_id) {
          if (!taskType || data.data.task_type === taskType) {
            fetchRunningTasks()
          }
        }
      } catch (error) {
        console.error("解析任务事件失败:", error)
      }
    }

    eventSource.addEventListener("task_updated", onTaskEvent)
    eventSource.addEventListener("task_created", onTaskEvent)

    eventSource.addEventListener("connected", () => {
      if (fallbackIntervalRef.current) {
        clearInterval(fallbackIntervalRef.current)
        fallbackIntervalRef.current = null
      }
    })

    eventSource.onerror = () => {
      if (eventSource.readyState === EventSource.CLOSED && !fallbackIntervalRef.current) {
        fallbackIntervalRef.current = setInterval(() => {
          fetchRunningTasks()
        }, 30000)
      }
    }

    return () => {
      if (fallbackIntervalRef.current) {
        clearInterval(fallbackIntervalRef.current)
        fallbackIntervalRef.current = null
      }
      eventSource.close()
      eventSourceRef.current = null
    }
  }, [taskType, fetchRunningTasks])

  return {
    tasks,
    isLoading,
    refetch: fetchRunningTasks,
  }
}
