// 设置API
import { apiClient } from "./client"

export interface AppConfig {
  manual_manga_site_url: string | null
  // 最近更新の検索で「漢化」作品のみ取得するか（既定 true）
  recent_updates_hanhua_only: boolean
  // 各画面の「最后更新」表示用（ISO 文字列 or null）
  collection_synced_at: string | null
  recent_synced_at: string | null
}

export interface AppConfigUpdate {
  manual_manga_site_url?: string | null
  recent_updates_hanhua_only?: boolean
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

