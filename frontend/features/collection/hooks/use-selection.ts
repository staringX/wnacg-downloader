// 选择功能相关的 hooks
"use client"

import { useState } from "react"
import type { MangaItem } from "@/lib/types"

export function useSelection() {
  const [selectionMode, setSelectionMode] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  const handleToggleSelect = (manga: MangaItem) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(manga.id)) {
        next.delete(manga.id)
      } else {
        next.add(manga.id)
      }
      return next
    })
  }

  const handleToggleSelectionMode = () => {
    setSelectionMode((prev) => !prev)
    setSelectedIds(new Set())
  }

  const clearSelection = () => {
    setSelectedIds(new Set())
    setSelectionMode(false)
  }

  return {
    selectionMode,
    selectedIds,
    handleToggleSelect,
    handleToggleSelectionMode,
    clearSelection,
    setSelectedIds,
  }
}

