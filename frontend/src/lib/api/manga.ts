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

  // 将漫画添加到网站收藏夹（对应作者文件夹）
  async addToFavorite(mangaId: string): Promise<ApiResponse<{ success: boolean; message: string }>> {
    return apiClient.post<{ success: boolean; message: string }>("/api/add-to-favorite", { manga_id: mangaId })
  },
}

