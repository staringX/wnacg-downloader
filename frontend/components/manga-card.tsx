"use client"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Download, Check, Clock, HardDrive, Loader2, X, CheckCircle2, BookOpen } from "lucide-react"
import type { MangaItem } from "@/lib/types"
import Image from "next/image"
import { useState } from "react"

interface MangaCardProps {
  manga: MangaItem
  onDownload?: (manga: MangaItem) => void
  onDelete?: (manga: MangaItem) => void
  isDownloading?: boolean
  showPreview?: boolean
  selectionMode?: boolean
  isSelected?: boolean
  onToggleSelect?: (manga: MangaItem) => void
}

export function MangaCard({
  manga,
  onDownload,
  onDelete,
  isDownloading,
  showPreview = false,
  selectionMode = false,
  isSelected = false,
  onToggleSelect,
}: MangaCardProps) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const isDownloaded = !!manga.downloaded_at || manga.is_downloaded

  const formatFileSize = (bytes: number | null) => {
    if (!bytes) return "N/A"
    const mb = bytes / (1024 * 1024)
    return `${mb.toFixed(2)} MB`
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "N/A"
    return new Date(dateString).toLocaleDateString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    })
  }

  const handleDeleteClick = () => {
    setShowDeleteConfirm(true)
  }

  const handleConfirmDelete = () => {
    onDelete?.(manga)
    setShowDeleteConfirm(false)
  }

  const handleCancelDelete = () => {
    setShowDeleteConfirm(false)
  }

  const handleCardClick = () => {
    if (selectionMode && onToggleSelect) {
      onToggleSelect(manga)
    } else {
      // Navigate to manga URL
      window.open(manga.manga_url, "_blank")
    }
  }

  return (
    <>
      <Card
        onClick={handleCardClick}
        className={`${
          isDownloaded
            ? "glass-card border-primary/30 bg-gradient-to-br from-primary/10 to-primary/5 relative group cursor-pointer hover:scale-105 hover:shadow-xl transition-all duration-300"
            : "glass-card hover:shadow-xl transition-all duration-300 relative group cursor-pointer hover:scale-105"
        } ${selectionMode ? "" : ""} ${isSelected ? "ring-2 ring-primary shadow-lg" : ""}`}
      >
        {selectionMode && isSelected && (
          <div className="absolute -top-1.5 -left-1.5 w-5 h-5 rounded-full bg-primary flex items-center justify-center shadow-md z-10">
            <CheckCircle2 className="w-3.5 h-3.5 text-primary-foreground" />
          </div>
        )}

        {/* Left: Green check for downloaded status - floating on top-left corner */}
        {!selectionMode && isDownloaded && !isDownloading && (
          <div className="absolute -top-1.5 -left-1.5 w-4 h-4 rounded-full bg-green-500 flex items-center justify-center shadow-md z-10">
            <Check className="w-2.5 h-2.5 text-white" />
          </div>
        )}

        {/* Downloading indicator - floating on top-left corner */}
        {!selectionMode && isDownloading && (
          <div className="absolute -top-1.5 -left-1.5 w-4 h-4 rounded-full bg-blue-500 flex items-center justify-center shadow-md z-10">
            <Loader2 className="w-2.5 h-2.5 text-white animate-spin" />
          </div>
        )}

        {/* Right: Red X delete button - floating on top-right corner, only visible on hover */}
        {!selectionMode && onDelete && isDownloaded && (
          <Button
            onClick={(e) => {
              e.stopPropagation() // Prevent card click when clicking delete
              handleDeleteClick()
            }}
            size="icon"
            className="absolute -top-1.5 -right-1.5 h-4 w-4 rounded-full bg-red-500 hover:bg-red-600 text-white shadow-md opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10 p-0"
          >
            <X className="w-2.5 h-2.5" />
          </Button>
        )}

        {!selectionMode && !isDownloaded && onDownload && (
          <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10">
            <Button
              onClick={(e) => {
                e.stopPropagation()
                onDownload(manga)
              }}
              disabled={isDownloading}
              size="icon"
              className="h-12 w-12 rounded-full bg-black/50 backdrop-blur-md hover:bg-black/60 text-white shadow-lg hover:scale-110 active:scale-95 transition-all duration-200 border border-white/20"
            >
              {isDownloading ? <Loader2 className="w-6 h-6 animate-spin" /> : <Download className="w-6 h-6" />}
            </Button>
          </div>
        )}

        {showPreview && manga.preview_image_url && (
          <div className="relative w-full aspect-[2/3] overflow-hidden rounded-t-lg max-w-[120px] mx-auto mt-2">
            <Image
              src={manga.preview_image_url || "/placeholder.svg"}
              alt={manga.title}
              fill
              className="object-cover"
              sizes="120px"
            />
          </div>
        )}

        <CardHeader className={showPreview ? "pb-2 pt-3" : "pb-1.5 pt-3 px-3"}>
          <h3
            className={`font-semibold leading-tight line-clamp-2 text-balance ${showPreview ? "text-base" : "text-sm"}`}
          >
            {manga.title}
          </h3>
        </CardHeader>

        <div className="h-px bg-gradient-to-r from-transparent via-border to-transparent mx-3" />

        <CardContent className={showPreview ? "pb-2 pt-1.5 px-3" : "pb-1.5 pt-1 px-3"}>
          <div className="space-y-0.5">
            <div
              className={`flex items-center gap-2 text-muted-foreground flex-wrap ${showPreview ? "text-xs" : "text-[10px]"}`}
            >
              <div className="flex items-center gap-0.5">
                <BookOpen className={showPreview ? "w-3 h-3" : "w-2.5 h-2.5"} />
                <span>{manga.page_count || 0}页</span>
              </div>

              <div className="flex items-center gap-0.5">
                <HardDrive className={showPreview ? "w-3 h-3" : "w-2.5 h-2.5"} />
                <span>{formatFileSize(manga.file_size)}</span>
              </div>

              <div className="flex items-center gap-0.5">
                <Clock className={showPreview ? "w-3 h-3" : "w-2.5 h-2.5"} />
                <span>{formatDate(manga.updated_at)}</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="glass-card p-6 max-w-sm mx-4 space-y-4">
            <h3 className="text-lg font-semibold">确认删除</h3>
            <p className="text-sm text-muted-foreground">确定要删除《{manga.title}》吗？此操作无法撤销。</p>
            <div className="flex gap-3 justify-end">
              <Button onClick={handleCancelDelete} variant="outline" className="glass-card bg-transparent">
                取消
              </Button>
              <Button onClick={handleConfirmDelete} className="bg-red-500 hover:bg-red-600 text-white">
                确认删除
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
