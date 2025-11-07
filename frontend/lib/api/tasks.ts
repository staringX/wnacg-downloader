// 任务相关 API
import { apiClient } from "./client"
import type { ApiResponse, TaskStatus } from "../types"

export const tasksApi = {
  // 获取任务状态
  async getTaskStatus(taskId: string): Promise<ApiResponse<TaskStatus>> {
    return apiClient.get<TaskStatus>(`/api/tasks/${taskId}`)
  },

  // 获取正在运行的任务列表
  async getRunningTasks(taskType?: string): Promise<ApiResponse<TaskStatus[]>> {
    const endpoint = taskType
      ? `/api/tasks/running/list?task_type=${taskType}`
      : "/api/tasks/running/list"
    return apiClient.get<TaskStatus[]>(endpoint)
  },
}

