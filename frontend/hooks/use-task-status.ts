"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import type { TaskStatus } from "@/lib/types"

export function useTaskStatus(taskId: string | null) {
  const [task, setTask] = useState<TaskStatus | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)
  const fallbackIntervalRef = useRef<NodeJS.Timeout | null>(null)

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
      // 连接成功时，清除备用轮询
      if (fallbackIntervalRef.current) {
        clearInterval(fallbackIntervalRef.current)
        fallbackIntervalRef.current = null
        console.log("SSE连接已恢复，停止备用轮询")
      }
    })
    
    // 错误处理
    eventSource.onerror = (error) => {
      console.error("SSE连接错误:", error)
      // 连接断开时，定期查询任务状态作为备用
      if (eventSource.readyState === EventSource.CLOSED && !fallbackIntervalRef.current) {
        console.log("SSE连接断开，启用备用轮询（每10秒）")
        fallbackIntervalRef.current = setInterval(() => {
          fetchTask()
        }, 10000) // 每10秒查询一次（降低频率）
      }
    }

    // 清理函数
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

// 获取正在运行的任务列表
export function useRunningTasks(taskType?: string) {
  const [tasks, setTasks] = useState<TaskStatus[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)
  const fallbackIntervalRef = useRef<NodeJS.Timeout | null>(null)

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

  // 初始化时查询一次
  useEffect(() => {
    fetchRunningTasks()
  }, [fetchRunningTasks])

  // 建立SSE连接监听任务状态更新（通过SSE更新任务列表，而不是轮询）
  useEffect(() => {
    // 创建EventSource连接
    const eventSource = new EventSource(
      `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/events`
    )
    eventSourceRef.current = eventSource

    // 监听任务更新事件，更新任务列表
    eventSource.addEventListener("task_updated", (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.data?.task_id) {
          // 如果任务状态变化，刷新任务列表
          // 只刷新与当前taskType相关的任务
          if (!taskType || data.data.task_type === taskType) {
            fetchRunningTasks()
          }
        }
      } catch (error) {
        console.error("解析任务更新事件失败:", error)
      }
    })

    // 监听任务创建事件
    eventSource.addEventListener("task_created", (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.data?.task_id) {
          // 如果新任务创建，刷新任务列表
          if (!taskType || data.data.task_type === taskType) {
            fetchRunningTasks()
          }
        }
      } catch (error) {
        console.error("解析任务创建事件失败:", error)
      }
    })

    // 监听连接事件
    eventSource.addEventListener("connected", (event) => {
      console.log("SSE连接已建立（运行中任务列表）")
      // 连接成功时，清除备用轮询
      if (fallbackIntervalRef.current) {
        clearInterval(fallbackIntervalRef.current)
        fallbackIntervalRef.current = null
        console.log("SSE连接已恢复，停止备用轮询（运行中任务列表）")
      }
    })

    // 错误处理（SSE断开时，使用低频轮询作为备用）
    eventSource.onerror = (error) => {
      console.error("SSE连接错误（运行中任务列表）:", error)
      // 连接断开时，使用低频轮询作为备用（每30秒一次）
      if (eventSource.readyState === EventSource.CLOSED && !fallbackIntervalRef.current) {
        console.log("SSE连接断开，启用备用轮询（每30秒）")
        fallbackIntervalRef.current = setInterval(() => {
          fetchRunningTasks()
        }, 30000) // 每30秒查询一次（降低频率）
      }
    }

    // 清理函数
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

