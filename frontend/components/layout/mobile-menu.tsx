// 移动端菜单组件
"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import {
  Menu,
  CheckCircle2,
  X,
  Download,
  RefreshCw,
  ExternalLink,
  FileCheck,
  Settings,
} from "lucide-react"

interface MobileMenuProps {
  showPreview: boolean
  onPreviewChange: (show: boolean) => void
  selectionMode: boolean
  onToggleSelectionMode: () => void
  selectedCount: number
  onBatchDelete: () => void
  pendingCount: number
  onDownloadAll: () => void
  onSync: () => void
  isSyncing: boolean
  syncProgressText: string
  currentTab: "collection" | "updates"
  groupByAuthor: boolean
  onGroupByAuthorChange: (value: boolean) => void
  onUpdateDownloadStatus: () => void
  isUpdatingStatus: boolean
  onOpenSettings: () => void
}

export function MobileMenu({
  showPreview,
  onPreviewChange,
  selectionMode,
  onToggleSelectionMode,
  selectedCount,
  onBatchDelete,
  pendingCount,
  onDownloadAll,
  onSync,
  isSyncing,
  syncProgressText,
  currentTab,
  groupByAuthor,
  onGroupByAuthorChange,
  onUpdateDownloadStatus,
  isUpdatingStatus,
  onOpenSettings,
}: MobileMenuProps) {
  const [sheetOpen, setSheetOpen] = useState(false)

  // 跳转到 Komga - 直接打开 Komga 的完整 URL（避免通过 Next.js 代理导致的 SPA 路径问题）
  const handleOpenKomga = () => {
    if (typeof window !== "undefined") {
      // 使用当前页面的协议和主机名，端口使用 Komga 的端口
      const komgaUrl = `${window.location.protocol}//${window.location.hostname}:25601`
      window.open(komgaUrl, "_blank")
    }
  }

  const handleOpenSettings = () => {
    setSheetOpen(false) // 先关闭移动端菜单
    onOpenSettings() // 然后打开设置对话框
  }

  return (
    <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
      <SheetTrigger asChild>
        <Button
          size="icon"
          className="fixed top-4 right-4 z-50 h-12 w-12 rounded-full bg-primary/80 backdrop-blur-md text-primary-foreground shadow-lg hover:bg-primary/90 hover:scale-110 active:scale-95 transition-all duration-200 lg:hidden border border-primary/20"
        >
          <Menu className="h-6 w-6" />
        </Button>
      </SheetTrigger>
      <SheetContent side="right" className="w-80 sm:w-96">
        <SheetHeader>
          <SheetTitle>菜单</SheetTitle>
        </SheetHeader>
        <div className="mt-6 space-y-4">
          {/* 设置按钮 */}
          <Button
            onClick={handleOpenSettings}
            variant="outline"
            className="w-full justify-start h-12 text-base glass-card hover:shadow-lg transition-all bg-transparent"
          >
            <Settings className="w-5 h-5 mr-3" />
            设置
          </Button>

          {/* 跳转到 Komga 按钮 */}
          <Button
            onClick={handleOpenKomga}
            variant="outline"
            className="w-full justify-start h-12 text-base glass-card hover:shadow-lg transition-all bg-transparent"
          >
            <ExternalLink className="w-5 h-5 mr-3" />
            Komga
          </Button>

          {/* 多选模式 */}
          <Button
            onClick={onToggleSelectionMode}
            variant={selectionMode ? "default" : "outline"}
            className="w-full justify-start h-12 text-base"
          >
            <CheckCircle2 className="w-5 h-5 mr-3" />
            {selectionMode ? "退出多选" : "多选"}
          </Button>

          {/* 删除选中 */}
          {selectionMode && selectedCount > 0 && (
            <Button
              onClick={onBatchDelete}
              className="w-full justify-start h-12 text-base bg-red-500 text-white hover:bg-red-600"
            >
              <X className="w-5 h-5 mr-3" />
              删除 ({selectedCount})
            </Button>
          )}

          {/* 更新下载状态按钮 */}
          <Button
            onClick={onUpdateDownloadStatus}
            disabled={isUpdatingStatus}
            variant="outline"
            className="w-full justify-start h-12 text-base glass-card hover:shadow-lg transition-all bg-transparent"
            title="扫描本地下载文件并更新数据库中的下载状态"
          >
            <FileCheck className={`w-5 h-5 mr-3 ${isUpdatingStatus ? "animate-spin" : ""}`} />
            {isUpdatingStatus ? "更新中..." : "更新状态"}
          </Button>

          {/* 统一的同步按钮 */}
          <Button
            onClick={onSync}
            disabled={isSyncing}
            variant="outline"
            className="w-full justify-start h-12 text-base glass-card hover:shadow-lg transition-all bg-transparent"
          >
            <RefreshCw className={`w-5 h-5 mr-3 ${isSyncing ? "animate-spin" : ""}`} />
            {isSyncing ? `同步中${syncProgressText}` : "同步"}
          </Button>

          {/* 统一的全部下载按钮 */}
          {!selectionMode && pendingCount > 0 && (
            <Button
              onClick={onDownloadAll}
              className="w-full justify-start h-12 text-base bg-primary text-primary-foreground hover:bg-primary/90"
            >
              <Download className="w-5 h-5 mr-3" />
              下载全部 ({pendingCount})
            </Button>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}

