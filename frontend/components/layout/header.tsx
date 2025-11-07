// 页面头部组件
"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Download, ImageIcon, CheckCircle2, X } from "lucide-react"
import { SyncButton } from "@/components/common/sync-button"
import { MobileMenu } from "./mobile-menu"

interface HeaderProps {
  totalMangas: number
  downloadedMangas: number
  pendingMangas: number
  showPreview: boolean
  onPreviewChange: (show: boolean) => void
  selectionMode: boolean
  onToggleSelectionMode: () => void
  selectedCount: number
  onBatchDelete: () => void
  onDownloadAllPending: () => void
  onSyncComplete: () => void
}

export function Header({
  totalMangas,
  downloadedMangas,
  pendingMangas,
  showPreview,
  onPreviewChange,
  selectionMode,
  onToggleSelectionMode,
  selectedCount,
  onBatchDelete,
  onDownloadAllPending,
  onSyncComplete,
}: HeaderProps) {
  const [isScrolled, setIsScrolled] = useState(false)
  const [lastScrollY, setLastScrollY] = useState(0)
  const [isVisible, setIsVisible] = useState(true)
  const [isMobile, setIsMobile] = useState(false)

  // 检测是否为移动端
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 1024) // lg breakpoint
    }
    
    checkMobile()
    window.addEventListener("resize", checkMobile)
    return () => window.removeEventListener("resize", checkMobile)
  }, [])

  // 监听滚动，实现自动隐藏/显示（仅移动端）
  useEffect(() => {
    if (!isMobile) {
      setIsVisible(true)
      return
    }

    const handleScroll = () => {
      const currentScrollY = window.scrollY
      
      // 在顶部时始终显示
      if (currentScrollY < 10) {
        setIsScrolled(false)
        setIsVisible(true)
        setLastScrollY(currentScrollY)
        return
      }

      setIsScrolled(true)
      
      // 向下滚动时隐藏，向上滚动时显示
      if (currentScrollY > lastScrollY && currentScrollY > 100) {
        setIsVisible(false)
      } else if (currentScrollY < lastScrollY) {
        setIsVisible(true)
      }
      
      setLastScrollY(currentScrollY)
    }

    window.addEventListener("scroll", handleScroll, { passive: true })
    return () => window.removeEventListener("scroll", handleScroll)
  }, [lastScrollY, isMobile])

  return (
    <>
      <header
        className={`glass-header sticky z-10 transition-transform duration-300 ${
          isVisible ? "translate-y-0" : "-translate-y-full"
        } ${isScrolled ? "shadow-lg" : ""}`}
        style={{ top: 0 }}
      >
        <div className="container mx-auto px-4 py-4">
          {/* 桌面端布局 - 完全保持原样 */}
          <div className="hidden lg:flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-balance bg-gradient-to-r from-primary via-primary/80 to-primary/60 bg-clip-text text-transparent">
                漫画下载管理器
              </h1>
              <p className="text-sm text-muted-foreground mt-1">
                总计: {totalMangas} | 已下载: {downloadedMangas} | 待下载: {pendingMangas}
              </p>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 glass-card px-3 py-2 rounded-lg">
                <ImageIcon className="w-4 h-4 text-muted-foreground" />
                <Label htmlFor="preview-toggle" className="text-sm cursor-pointer">
                  预览图
                </Label>
                <Switch id="preview-toggle" checked={showPreview} onCheckedChange={onPreviewChange} />
              </div>

              <Button
                onClick={onToggleSelectionMode}
                variant={selectionMode ? "default" : "outline"}
                className={
                  selectionMode
                    ? "bg-primary text-primary-foreground"
                    : "glass-card bg-transparent hover:bg-primary/10"
                }
              >
                <CheckCircle2 className="w-4 h-4 mr-2" />
                {selectionMode ? "退出多选" : "多选模式"}
              </Button>

              {selectionMode && selectedCount > 0 && (
                <Button
                  onClick={onBatchDelete}
                  className="bg-red-500 text-white hover:bg-red-600 hover:scale-105 active:scale-95 transition-all duration-200 shadow-lg"
                >
                  <X className="w-4 h-4 mr-2" />
                  删除选中 ({selectedCount})
                </Button>
              )}

              <SyncButton onSyncComplete={onSyncComplete} />
              {!selectionMode && pendingMangas > 0 && (
                <Button
                  onClick={onDownloadAllPending}
                  className="bg-primary text-primary-foreground hover:bg-primary/90 hover:scale-105 active:scale-95 transition-all duration-200 shadow-lg"
                >
                  <Download className="w-4 h-4 mr-2" />
                  下载全部待下载 ({pendingMangas})
                </Button>
              )}
            </div>
          </div>

          {/* 移动端布局 - 只显示标题和统计信息 */}
          <div className="lg:hidden">
            <div>
              <h1 className="text-xl font-bold text-balance bg-gradient-to-r from-primary via-primary/80 to-primary/60 bg-clip-text text-transparent">
                漫画下载管理器
              </h1>
              <p className="text-xs text-muted-foreground mt-1">
                总计: {totalMangas} | 已下载: {downloadedMangas} | 待下载: {pendingMangas}
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* 移动端菜单按钮 - 悬浮在右上角 */}
      <div className="lg:hidden">
        <MobileMenu
          showPreview={showPreview}
          onPreviewChange={onPreviewChange}
          selectionMode={selectionMode}
          onToggleSelectionMode={onToggleSelectionMode}
          selectedCount={selectedCount}
          onBatchDelete={onBatchDelete}
          pendingMangas={pendingMangas}
          onDownloadAllPending={onDownloadAllPending}
          onSyncComplete={onSyncComplete}
        />
      </div>
    </>
  )
}

