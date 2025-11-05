const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
}

export const api = {
  // Fetch all mangas from collection
  async fetchMangas(): Promise<ApiResponse<any[]>> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/mangas`)
      if (!response.ok) throw new Error("Failed to fetch mangas")
      const data = await response.json()
      return { success: true, data }
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : "Unknown error" }
    }
  },

  // Sync collection from manga website
  async syncCollection(): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/sync`, { method: "POST" })
      if (!response.ok) throw new Error("Failed to sync collection")
      const data = await response.json()
      return { success: true, data }
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : "Unknown error" }
    }
  },

  // Download a single manga
  async downloadManga(mangaId: string): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/download/${mangaId}`, { method: "POST" })
      if (!response.ok) throw new Error("Failed to download manga")
      const data = await response.json()
      return { success: true, data }
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : "Unknown error" }
    }
  },

  // Download multiple mangas
  async downloadBatch(mangaIds: string[]): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/download/batch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ manga_ids: mangaIds }),
      })
      if (!response.ok) throw new Error("Failed to download batch")
      const data = await response.json()
      return { success: true, data }
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : "Unknown error" }
    }
  },

  // Fetch recent updates
  async fetchRecentUpdates(): Promise<ApiResponse<any[]>> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/recent-updates`)
      if (!response.ok) throw new Error("Failed to fetch recent updates")
      const data = await response.json()
      return { success: true, data }
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : "Unknown error" }
    }
  },

  async deleteManga(mangaId: string): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/manga/${mangaId}`, { method: "DELETE" })
      if (!response.ok) throw new Error("Failed to delete manga")
      const data = await response.json()
      return { success: true, data }
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : "Unknown error" }
    }
  },
}
