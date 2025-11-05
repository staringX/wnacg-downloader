"use client"

import { useState } from "react"
import { MangaCard } from "./manga-card"
import { Button } from "@/components/ui/button"
import { Download, Sparkles, RefreshCw } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import type { RecentUpdate } from "@/lib/types"
import { api } from "@/lib/api"
import { mockRecentUpdates } from "@/lib/mock-data"

interface RecentUpdatesProps {
  onDownload: (manga: RecentUpdate) => void
  onDelete: (manga: RecentUpdate) => void // Added delete callback
  downloadingIds: Set<string>
  showPreview?: boolean
}

export function RecentUpdates({ onDownload, onDelete, downloadingIds, showPreview = false }: RecentUpdatesProps) {
  const [updates, setUpdates] = useState<RecentUpdate[]>(mockRecentUpdates)
  const [isLoading, setIsLoading] = useState(false)
  const { toast } = useToast()

  const handleRefresh = async () => {
    setIsLoading(true)
    try {
      const response = await api.fetchRecentUpdates()
      if (response.success && response.data) {
        setUpdates(response.data)
        toast({
          title: "更新成功",
          description: `获取到 ${response.data.length} 个最近更新`,
        })
      } else {
        toast({
          title: "更新失败",
          description: "使用本地数据",
          variant: "destructive",
        })
      }
    } catch (error) {
      console.error("[v0] Refresh recent updates error:", error)
      toast({
        title: "更新失败",
        description: "使用本地数据",
        variant: "destructive",
      })
    } finally {
      setIsLoading(false)
    }
  }

  const pendingUpdates = updates.filter((u) => !u.is_downloaded)

  const handleDownloadAll = async () => {
    if (pendingUpdates.length === 0) return

    for (const update of pendingUpdates) {
      await onDownload(update)
    }
  }

  if (updates.length === 0) {
    return (
      <div className="glass rounded-lg p-6">
        <div className="flex items-center gap-2 mb-4">
          <Sparkles className="w-5 h-5 text-primary" />
          <h2 className="text-2xl font-bold">收藏作者最近更新</h2>
        </div>
        <p className="text-muted-foreground text-center py-8">暂无收藏作者的更新</p>
      </div>
    )
  }

  return (
    <div className="glass rounded-lg overflow-hidden">
      <div className="glass-muted p-6 bg-gradient-to-r from-primary/10 via-primary/5 to-transparent">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary" />
            <h2 className="text-2xl font-bold">收藏作者最近更新</h2>
            <span className="text-sm text-muted-foreground glass-muted px-3 py-1 rounded-full">
              {updates.length - pendingUpdates.length}/{updates.length} 已下载
            </span>
          </div>

          <div className="flex items-center gap-2">
            <Button
              onClick={handleRefresh}
              variant="outline"
              size="sm"
              className="glass-card bg-transparent"
              disabled={isLoading}
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? "animate-spin" : ""}`} />
              {isLoading ? "更新中..." : "刷新更新"}
            </Button>

            {pendingUpdates.length > 0 && (
              <Button
                onClick={handleDownloadAll}
                variant="default"
                className="bg-primary text-primary-foreground hover:bg-primary/90 shadow-lg hover:shadow-xl transition-all duration-300"
              >
                <Download className="w-4 h-4 mr-2" />
                下载全部新更新 ({pendingUpdates.length})
              </Button>
            )}
          </div>
        </div>
      </div>

      <div className="p-6">
        <div
          className={`grid gap-3 ${showPreview ? "grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5" : "grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 2xl:grid-cols-10"}`}
        >
          {updates.map((update) => (
            <MangaCard
              key={update.id}
              manga={update}
              onDownload={onDownload}
              onDelete={onDelete}
              isDownloading={downloadingIds.has(update.id)}
              showPreview={showPreview}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
