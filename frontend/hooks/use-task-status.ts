"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { api } from "@/lib/api"

export interface TaskStatus {
  id: string
  task_type: string
  status: "pending" | "running" | "completed" | "failed"
  progress: number
  total_items?: number
  completed_items: number
  message?: string
  error_message?: string
  manga_id?: string
  manga_ids?: string
  result_data?: string
  created_at: string
  updated_at: string
  completed_at?: string
}

export function useTaskStatus(taskId: string | null) {
  const [task, setTask] = useState<TaskStatus | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)

  // 从数据库查询任务状态（用于页面刷新后恢复状态）
  const fetchTask = useCallback(async () => {
    if (!taskId) {
      setTask(null)
      return
    }

    setIsLoading(true)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/tasks/${taskId}`)
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

    // 创建EventSource连接
    const eventSource = new EventSource(
      `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/events`
    )
    eventSourceRef.current = eventSource

    // 监听任务创建事件
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

    // 监听任务更新事件
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

    // 监听连接事件
    eventSource.addEventListener("connected", (event) => {
      console.log("SSE连接已建立")
    })

    // 错误处理
    eventSource.onerror = (error) => {
      console.error("SSE连接错误:", error)
      // 连接断开时，定期查询任务状态作为备用
      if (eventSource.readyState === EventSource.CLOSED) {
        const interval = setInterval(() => {
          fetchTask()
        }, 2000) // 每2秒查询一次

        // 清理定时器
        return () => clearInterval(interval)
      }
    }

    // 清理函数
    return () => {
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

// 获取正在运行的任务列表
export function useRunningTasks(taskType?: string) {
  const [tasks, setTasks] = useState<TaskStatus[]>([])
  const [isLoading, setIsLoading] = useState(false)

  const fetchRunningTasks = useCallback(async () => {
    setIsLoading(true)
    try {
      const url = taskType
        ? `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/tasks/running/list?task_type=${taskType}`
        : `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/tasks/running/list`
      
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
    // 定期刷新（作为SSE的备用，但频率较低）
    const interval = setInterval(fetchRunningTasks, 5000) // 每5秒刷新一次
    return () => clearInterval(interval)
  }, [fetchRunningTasks])

  return {
    tasks,
    isLoading,
    refetch: fetchRunningTasks,
  }
}

