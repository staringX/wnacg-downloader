// 删除功能相关的 hooks
"use client"

import { mangaApi } from "@/lib/api"
import { useToast } from "@/hooks/use-toast"
import type { MangaItem, AuthorGroup } from "@/lib/types"

export function useDelete() {
  const { toast } = useToast()

  const handleDelete = async (
    manga: MangaItem,
    authorGroups: AuthorGroup[],
    setAuthorGroups: (groups: AuthorGroup[]) => void
  ) => {
    try {
      const response = await mangaApi.deleteManga(manga.id)

      if (response.success) {
        toast({
          title: "删除成功",
          description: manga.title,
        })

        // Remove manga from state
        setAuthorGroups(
          prev =>
            prev
              .map(ag => ({
                ...ag,
                mangas: ag.mangas.filter(m => m.id !== manga.id),
              }))
              .filter(ag => ag.mangas.length > 0) // Remove empty author groups
        )
      } else {
        throw new Error(response.error || "删除失败")
      }
    } catch (error) {
      console.error("Delete error:", error)
      toast({
        title: "删除失败",
        description: error instanceof Error ? error.message : "请稍后重试",
        variant: "destructive",
      })
    }
  }

  const handleBatchDelete = async (
    selectedIds: Set<string>,
    authorGroups: AuthorGroup[],
    setAuthorGroups: (groups: AuthorGroup[]) => void,
    clearSelection: () => void
  ) => {
    if (selectedIds.size === 0) {
      toast({
        title: "请先选择要删除的漫画",
        description: "点击漫画卡片进行选择",
      })
      return
    }

    if (confirm(`确定要删除选中的 ${selectedIds.size} 个漫画吗？此操作无法撤销。`)) {
      try {
        await Promise.all(Array.from(selectedIds).map(id => mangaApi.deleteManga(id)))

        toast({
          title: "批量删除成功",
          description: `已删除 ${selectedIds.size} 个漫画`,
        })

        setAuthorGroups(
          prev =>
            prev
              .map(ag => ({
                ...ag,
                mangas: ag.mangas.filter(m => !selectedIds.has(m.id)),
              }))
              .filter(ag => ag.mangas.length > 0)
        )

        clearSelection()
      } catch (error) {
        console.error("Batch delete error:", error)
        toast({
          title: "批量删除失败",
          description: error instanceof Error ? error.message : "请稍后重试",
          variant: "destructive",
        })
      }
    }
  }

  return {
    handleDelete,
    handleBatchDelete,
  }
}

