// 最近更新功能相关的 hooks
"use client"

import { useState, useEffect, useMemo } from "react"
import { recentUpdatesApi } from "@/lib/api"
import { mockRecentUpdates } from "@/lib/mock-data"
import type { RecentUpdate, AuthorGroup } from "@/lib/types"

export function useRecentUpdates(refreshTrigger: number = 0) {
  const [updates, setUpdates] = useState<RecentUpdate[]>([])
  const [isLoading, setIsLoading] = useState(false)

  const loadUpdates = async () => {
    setIsLoading(true)
    try {
      const response = await recentUpdatesApi.fetchRecentUpdates()
      if (response.success && response.data) {
        setUpdates(response.data)
      } else {
        setUpdates(mockRecentUpdates)
      }
    } catch (error) {
      console.error("Load recent updates error:", error)
      setUpdates(mockRecentUpdates)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadUpdates()
  }, [refreshTrigger])

  const pendingUpdates = useMemo(
    () => updates.filter((u) => !u.is_downloaded),
    [updates]
  )

  const authorGroups = useMemo<AuthorGroup[]>(() => {
    return updates.reduce((acc: AuthorGroup[], update: RecentUpdate) => {
      let authorGroup = acc.find((g) => g.author === update.author)
      if (!authorGroup) {
        authorGroup = { author: update.author, mangas: [] }
        acc.push(authorGroup)
      }
      authorGroup.mangas.push(update)
      return acc
    }, [])
  }, [updates])

  return {
    updates,
    isLoading,
    pendingUpdates,
    authorGroups,
    reload: loadUpdates,
  }
}

