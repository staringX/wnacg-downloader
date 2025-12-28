// 同步相关 API
import { apiClient } from "./client"
import type { ApiResponse } from "../types"

export interface UpdateDownloadStatusResponse {
  scanned_files: number
  matched_count: number
  marked_downloaded: number
  marked_not_downloaded: number
  unmatched_files: number
}

export const syncApi = {
  // 同步收藏夹
  async syncCollection(): Promise<ApiResponse<{ task_id: string; message: string }>> {
    return apiClient.post<{ task_id: string; message: string }>("/api/sync")
  },

  // 同步最近更新
  async syncRecentUpdates(): Promise<ApiResponse<{ task_id: string; message: string }>> {
    return apiClient.post<{ task_id: string; message: string }>("/api/sync-recent-updates")
  },

  // 更新下载状态（扫描本地文件并同步数据库）
  async updateDownloadStatus(): Promise<ApiResponse<UpdateDownloadStatusResponse>> {
    return apiClient.post<UpdateDownloadStatusResponse>("/api/update-download-status")
  },
}

