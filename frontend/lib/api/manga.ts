// 漫画相关 API
import { apiClient } from "./client"
import type { ApiResponse, MangaItem } from "../types"

export const mangaApi = {
  // 获取所有漫画
  async fetchMangas(): Promise<ApiResponse<MangaItem[]>> {
    return apiClient.get<MangaItem[]>("/api/mangas")
  },

  // 删除漫画
  async deleteManga(mangaId: string): Promise<ApiResponse<any>> {
    return apiClient.delete(`/api/manga/${mangaId}`)
  },
}

