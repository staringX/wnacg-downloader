// 下载相关 API
import { apiClient } from "./client"
import type { ApiResponse } from "../types"

export const downloadApi = {
  // 下载单个漫画
  async downloadManga(mangaId: string): Promise<ApiResponse<{ task_id: string; message: string }>> {
    return apiClient.post<{ task_id: string; message: string }>(`/api/download/${mangaId}`)
  },

  // 批量下载漫画
  async downloadBatch(mangaIds: string[]): Promise<ApiResponse<any>> {
    return apiClient.post("/api/download/batch", { manga_ids: mangaIds })
  },
}

