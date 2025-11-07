// API 统一导出
export * from "./client"
export * from "./manga"
export * from "./tasks"
export * from "./sync"
export * from "./download"
export * from "./recent-updates"

// 兼容旧代码的默认导出
import { mangaApi } from "./manga"
import { tasksApi } from "./tasks"
import { syncApi } from "./sync"
import { downloadApi } from "./download"
import { recentUpdatesApi } from "./recent-updates"

export const api = {
  ...mangaApi,
  ...tasksApi,
  ...syncApi,
  ...downloadApi,
  ...recentUpdatesApi,
  // 保持向后兼容
  fetchMangas: mangaApi.fetchMangas,
  deleteManga: mangaApi.deleteManga,
  getTaskStatus: tasksApi.getTaskStatus,
  getRunningTasks: tasksApi.getRunningTasks,
  syncCollection: syncApi.syncCollection,
  syncRecentUpdates: syncApi.syncRecentUpdates,
  downloadManga: downloadApi.downloadManga,
  downloadBatch: downloadApi.downloadBatch,
  fetchRecentUpdates: recentUpdatesApi.fetchRecentUpdates,
}

