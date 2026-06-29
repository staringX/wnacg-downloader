// 最近更新相关 API
import { apiClient } from "./client"
import type { ApiResponse, RecentUpdate } from "../types"

export const recentUpdatesApi = {
  // 获取最近更新
  async fetchRecentUpdates(): Promise<ApiResponse<RecentUpdate[]>> {
    return apiClient.get<RecentUpdate[]>("/api/recent-updates")
  },

  // 从最近更新下载漫画（会先添加到Manga表，标记为is_favorited=false）
  async downloadFromUpdate(updateId: string): Promise<ApiResponse<{ task_id: string; message: string }>> {
    return apiClient.post<{ task_id: string; message: string }>(`/api/download-from-update/${updateId}`)
  },

  // 将最近更新收藏到网站（以 RecentUpdate 的 id 为入参，参见后端 add-update-to-favorite）
  async addUpdateToFavorite(
    updateId: string
  ): Promise<ApiResponse<{ success: boolean; message: string }>> {
    return apiClient.post<{ success: boolean; message: string }>(
      `/api/add-update-to-favorite/${updateId}`
    )
  },
}

