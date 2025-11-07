// 同步相关 API
import { apiClient } from "./client"
import type { ApiResponse } from "../types"

export const syncApi = {
  // 同步收藏夹
  async syncCollection(): Promise<ApiResponse<{ task_id: string; message: string }>> {
    return apiClient.post<{ task_id: string; message: string }>("/api/sync")
  },

  // 同步最近更新
  async syncRecentUpdates(): Promise<ApiResponse<{ task_id: string; message: string }>> {
    return apiClient.post<{ task_id: string; message: string }>("/api/sync-recent-updates")
  },
}

