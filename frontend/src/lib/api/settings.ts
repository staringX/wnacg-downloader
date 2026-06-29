// 设置API
import { apiClient } from "./client"

export interface AppConfig {
  manual_manga_site_url: string | null
}

export interface AppConfigUpdate {
  manual_manga_site_url?: string | null
}

export const settingsApi = {
  // 获取设置
  async getSettings(): Promise<AppConfig> {
    const response = await apiClient.get<AppConfig>("/api/settings")
    if (!response.success || !response.data) {
      throw new Error(response.error || "获取设置失败")
    }
    return response.data
  },

  // 更新设置
  async updateSettings(update: AppConfigUpdate): Promise<AppConfig> {
    const response = await apiClient.put<AppConfig>("/api/settings", update)
    if (!response.success || !response.data) {
      throw new Error(response.error || "更新设置失败")
    }
    return response.data
  },
}

