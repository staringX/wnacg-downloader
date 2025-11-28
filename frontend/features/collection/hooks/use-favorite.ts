// 收藏功能相关的 hooks
"use client"

import { useState } from "react"
import { mangaApi } from "@/lib/api"
import { useToast } from "@/hooks/use-toast"
import type { MangaItem } from "@/lib/types"

export function useFavorite() {
  const { toast } = useToast()
  const [favoritingIds, setFavoritingIds] = useState<Set<string>>(new Set())

  const handleFavorite = async (manga: MangaItem) => {
    // 检查是否已收藏
    if (manga.is_favorited) {
      toast({
        title: "已收藏",
        description: "该漫画已收藏到网站",
        variant: "default",
      })
      return
    }

    // 检查是否正在收藏
    if (favoritingIds.has(manga.id)) {
      toast({
        title: "收藏进行中",
        description: "该漫画正在收藏中，请等待完成",
        variant: "default",
      })
      return
    }

    try {
      setFavoritingIds((prev) => new Set(prev).add(manga.id))

      const response = await mangaApi.addToFavorite(manga.id)

      if (response.success && response.data) {
        toast({
          title: "收藏成功",
          description: response.data.message || "已成功收藏到网站",
        })
        // 注意：这里不更新本地状态，因为需要重新加载数据才能获取最新的is_favorited状态
      } else {
        throw new Error(response.error || "收藏失败")
      }
    } catch (error) {
      console.error("Favorite error:", error)
      toast({
        title: "收藏失败",
        description: error instanceof Error ? error.message : "请稍后重试",
        variant: "destructive",
      })
    } finally {
      setFavoritingIds((prev) => {
        const next = new Set(prev)
        next.delete(manga.id)
        return next
      })
    }
  }

  return {
    favoritingIds,
    handleFavorite,
  }
}

