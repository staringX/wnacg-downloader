"use client"

import { useState } from "react"
import { MangaCard } from "./manga-card"
import { Button } from "@/components/ui/button"
import { ChevronDown, ChevronRight, Download } from "lucide-react"
import type { AuthorGroup, MangaItem } from "@/lib/types"

interface AuthorSectionProps {
  authorGroup: AuthorGroup
  onDownload: (manga: MangaItem) => void
  onDownloadAll: (mangas: MangaItem[]) => void
  onDelete: (manga: MangaItem) => void
  onFavorite?: (manga: MangaItem) => void  // 收藏回调
  downloadingIds: Set<string>
  showPreview?: boolean
  selectionMode?: boolean
  selectedIds?: Set<string>
  onToggleSelect?: (manga: MangaItem) => void
}

export function AuthorSection({
  authorGroup,
  onDownload,
  onDownloadAll,
  onDelete,
  onFavorite,
  downloadingIds,
  showPreview = false,
  selectionMode = false,
  selectedIds = new Set(),
  onToggleSelect,
}: AuthorSectionProps) {
  const [isExpanded, setIsExpanded] = useState(true)

  // 在多选模式下，显示所有漫画（包括未下载的），允许选择任何漫画进行删除
  const allMangas = authorGroup.mangas

  const pendingMangas = authorGroup.mangas.filter((m) => !m.downloaded_at && !m.is_downloaded)
  const downloadedCount = authorGroup.mangas.length - pendingMangas.length

  return (
    <div className="glass rounded-lg overflow-hidden">
      <div className="glass-muted p-4 bg-gradient-to-r from-muted/50 to-muted/30">
        <div className="flex items-center justify-between">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-2 hover:text-primary transition-colors"
          >
            {isExpanded ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
            <h2 className="text-xl font-bold">{authorGroup.author}</h2>
            <span className="text-sm text-muted-foreground glass-muted px-2 py-0.5 rounded-full">
              {selectionMode ? `共 ${allMangas.length} 个` : `${downloadedCount}/${authorGroup.mangas.length} 已下载`}
            </span>
          </button>

          {!selectionMode && pendingMangas.length > 0 && (
            <Button
              onClick={() => onDownloadAll(pendingMangas)}
              variant="outline"
              size="sm"
              className="glass-card bg-primary/10 hover:bg-primary/20 text-foreground border-primary/30 hover:scale-105 active:scale-95 transition-all duration-200"
            >
              <Download className="w-4 h-4 mr-2" />
              下载全部未下载 ({pendingMangas.length})
            </Button>
          )}
        </div>
      </div>

      {isExpanded && (
        <div className="p-4 max-h-[600px] overflow-y-auto">
          <div
            className={`grid gap-3 ${showPreview ? "grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 2xl:grid-cols-10" : "grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 2xl:grid-cols-10"}`}
          >
            {allMangas.map((manga) => (
              <MangaCard
                key={manga.id}
                manga={manga}
                onDownload={onDownload}
                onDelete={onDelete}
                onFavorite={onFavorite}
                isDownloading={downloadingIds.has(manga.id)}
                showPreview={showPreview}
                selectionMode={selectionMode}
                isSelected={selectedIds.has(manga.id)}
                onToggleSelect={onToggleSelect}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
