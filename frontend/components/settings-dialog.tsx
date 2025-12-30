"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { useToast } from "@/hooks/use-toast"
import { settingsApi, type AppConfig } from "@/lib/api/settings"
import { Settings, ImageIcon, Users } from "lucide-react"

interface SettingsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  showPreview: boolean
  onPreviewChange: (show: boolean) => void
  groupByAuthor: boolean
  onGroupByAuthorChange: (value: boolean) => void
}

export function SettingsDialog({
  open,
  onOpenChange,
  showPreview,
  onPreviewChange,
  groupByAuthor,
  onGroupByAuthorChange,
}: SettingsDialogProps) {
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [manualUrl, setManualUrl] = useState("")
  const { toast } = useToast()

  // 加载设置
  useEffect(() => {
    if (open) {
      loadSettings()
    }
  }, [open])

  const loadSettings = async () => {
    setLoading(true)
    try {
      const config = await settingsApi.getSettings()
      setManualUrl(config.manual_manga_site_url || "")
    } catch (error) {
      toast({
        title: "加载设置失败",
        description: error instanceof Error ? error.message : "未知错误",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await settingsApi.updateSettings({
        manual_manga_site_url: manualUrl.trim() || null,
      })
      toast({
        title: "设置已保存",
        description: "设置已更新",
      })
      onOpenChange(false)
    } catch (error) {
      toast({
        title: "保存设置失败",
        description: error instanceof Error ? error.message : "未知错误",
        variant: "destructive",
      })
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg sm:text-xl">
            <Settings className="w-5 h-5 sm:w-6 sm:h-6" />
            设置
          </DialogTitle>
          <DialogDescription className="text-sm sm:text-base">
            配置应用设置，包括漫画网站链接、显示选项等。
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 sm:space-y-6 py-2 sm:py-4">
          {/* 漫画网站链接设置 */}
          <div className="space-y-2">
            <Label htmlFor="manual-url" className="text-sm sm:text-base">
              手动设置漫画网站链接
            </Label>
            <Input
              id="manual-url"
              type="url"
              placeholder="https://example.com"
              value={manualUrl}
              onChange={(e) => setManualUrl(e.target.value)}
              disabled={loading || saving}
              className="text-sm sm:text-base h-10 sm:h-11"
            />
            <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
              留空则使用自动获取的链接。URL必须以 http:// 或 https:// 开头。
            </p>
          </div>

          {/* 显示选项 */}
          <div className="space-y-3 sm:space-y-4 border-t pt-3 sm:pt-4">
            <Label className="text-sm sm:text-base font-semibold">显示选项</Label>
            
            {/* 预览开关 */}
            <div className="flex items-start sm:items-center justify-between gap-3 sm:gap-4">
              <div className="flex items-start sm:items-center gap-2 sm:gap-3 flex-1 min-w-0">
                <ImageIcon className="w-4 h-4 sm:w-5 sm:h-5 text-muted-foreground flex-shrink-0 mt-0.5 sm:mt-0" />
                <div className="space-y-0.5 flex-1 min-w-0">
                  <Label 
                    htmlFor="preview-toggle" 
                    className="text-sm sm:text-base font-normal cursor-pointer block"
                  >
                    显示预览图
                  </Label>
                  <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                    在漫画列表中显示封面预览图
                  </p>
                </div>
              </div>
              <Switch
                id="preview-toggle"
                checked={showPreview}
                onCheckedChange={onPreviewChange}
                disabled={loading || saving}
                className="flex-shrink-0"
              />
            </div>

            {/* 按作者分类开关 */}
            <div className="flex items-start sm:items-center justify-between gap-3 sm:gap-4">
              <div className="flex items-start sm:items-center gap-2 sm:gap-3 flex-1 min-w-0">
                <Users className="w-4 h-4 sm:w-5 sm:h-5 text-muted-foreground flex-shrink-0 mt-0.5 sm:mt-0" />
                <div className="space-y-0.5 flex-1 min-w-0">
                  <Label 
                    htmlFor="group-by-author-toggle" 
                    className="text-sm sm:text-base font-normal cursor-pointer block"
                  >
                    按作者分类
                  </Label>
                  <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                    将漫画按作者分组显示
                  </p>
                </div>
              </div>
              <Switch
                id="group-by-author-toggle"
                checked={groupByAuthor}
                onCheckedChange={onGroupByAuthorChange}
                disabled={loading || saving}
                className="flex-shrink-0"
              />
            </div>
          </div>
        </div>
        <DialogFooter className="flex-col sm:flex-row gap-2 sm:gap-0">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={saving}
            className="w-full sm:w-auto order-2 sm:order-1"
          >
            关闭
          </Button>
          <Button 
            onClick={handleSave} 
            disabled={loading || saving}
            className="w-full sm:w-auto order-1 sm:order-2"
          >
            {saving ? "保存中..." : "保存链接设置"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

