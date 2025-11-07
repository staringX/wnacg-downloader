// 移动端菜单组件
"use client"

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
  ImageIcon,
  CheckCircle2,
  X,
  Download,
} from "lucide-react"
import { SyncButton } from "@/components/common/sync-button"

interface MobileMenuProps {
  showPreview: boolean
  onPreviewChange: (show: boolean) => void
  selectionMode: boolean
  onToggleSelectionMode: () => void
  selectedCount: number
  onBatchDelete: () => void
  pendingMangas: number
  onDownloadAllPending: () => void
  onSyncComplete: () => void
}

export function MobileMenu({
  showPreview,
  onPreviewChange,
  selectionMode,
  onToggleSelectionMode,
  selectedCount,
  onBatchDelete,
  pendingMangas,
  onDownloadAllPending,
  onSyncComplete,
}: MobileMenuProps) {
  return (
    <Sheet>
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
          {/* 预览图开关 */}
          <div className="flex items-center justify-between glass-card px-4 py-3 rounded-lg">
            <div className="flex items-center gap-3">
              <ImageIcon className="w-5 h-5 text-muted-foreground" />
              <Label htmlFor="mobile-preview-toggle" className="text-base cursor-pointer">
                显示预览图
              </Label>
            </div>
            <Switch
              id="mobile-preview-toggle"
              checked={showPreview}
              onCheckedChange={onPreviewChange}
            />
          </div>

          {/* 多选模式 */}
          <Button
            onClick={onToggleSelectionMode}
            variant={selectionMode ? "default" : "outline"}
            className="w-full justify-start h-12 text-base"
          >
            <CheckCircle2 className="w-5 h-5 mr-3" />
            {selectionMode ? "退出多选模式" : "进入多选模式"}
          </Button>

          {/* 删除选中 */}
          {selectionMode && selectedCount > 0 && (
            <Button
              onClick={onBatchDelete}
              className="w-full justify-start h-12 text-base bg-red-500 text-white hover:bg-red-600"
            >
              <X className="w-5 h-5 mr-3" />
              删除选中 ({selectedCount})
            </Button>
          )}

          {/* 同步收藏夹 */}
          <div className="w-full [&>button]:w-full [&>button]:justify-start [&>button]:h-12 [&>button]:text-base">
            <SyncButton onSyncComplete={onSyncComplete} />
          </div>

          {/* 下载全部待下载 */}
          {!selectionMode && pendingMangas > 0 && (
            <Button
              onClick={onDownloadAllPending}
              className="w-full justify-start h-12 text-base bg-primary text-primary-foreground hover:bg-primary/90"
            >
              <Download className="w-5 h-5 mr-3" />
              下载全部待下载 ({pendingMangas})
            </Button>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}

