// 收藏功能相关的 hooks
"use client"

import { useState, useEffect, useCallback } from "react"
import { mangaApi } from "@/lib/api"
import { mockAllMangas } from "@/lib/mock-data"
import type { AuthorGroup, MangaItem } from "@/lib/types"

export function useCollection() {
  const [authorGroups, setAuthorGroups] = useState<AuthorGroup[]>([])
  const [isLoading, setIsLoading] = useState(true)

  const loadMangas = useCallback(async () => {
    setIsLoading(true)
    try {
      const response = await mangaApi.fetchMangas()
      let mangas: MangaItem[]

      if (response.success && response.data) {
        mangas = response.data
      } else {
        // Fallback to mock data if API fails
        mangas = mockAllMangas
      }

      const grouped = mangas.reduce((acc: AuthorGroup[], manga: MangaItem) => {
        let authorGroup = acc.find((g) => g.author === manga.author)
        if (!authorGroup) {
          authorGroup = { author: manga.author, mangas: [] }
          acc.push(authorGroup)
        }
        authorGroup.mangas.push(manga)
        return acc
      }, [])

      setAuthorGroups(grouped)
    } catch (error) {
      console.error("Load error:", error)
      // Fallback to mock data
      const mangas = mockAllMangas
      const grouped = mangas.reduce((acc: AuthorGroup[], manga: MangaItem) => {
        let authorGroup = acc.find((g) => g.author === manga.author)
        if (!authorGroup) {
          authorGroup = { author: manga.author, mangas: [] }
          acc.push(authorGroup)
        }
        authorGroup.mangas.push(manga)
        return acc
      }, [])
      setAuthorGroups(grouped)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadMangas()
  }, [loadMangas])

  return {
    authorGroups,
    isLoading,
    reload: loadMangas,
    setAuthorGroups,
  }
}

