// 最近更新相关 API
import { apiClient } from "./client"
import type { ApiResponse, RecentUpdate } from "../types"

export const recentUpdatesApi = {
  // 获取最近更新
  async fetchRecentUpdates(): Promise<ApiResponse<RecentUpdate[]>> {
    return apiClient.get<RecentUpdate[]>("/api/recent-updates")
  },
}

