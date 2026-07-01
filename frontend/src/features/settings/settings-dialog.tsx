import { useEffect, useState } from "react"
import * as Dialog from "@radix-ui/react-dialog"
import { Settings as SettingsIcon, X, Loader2, FileCheck } from "lucide-react"
import { settingsApi, syncApi } from "@/lib/api"
import type { AppConfig } from "@/lib/api"
import { Switch } from "@/components/common/switch"
import { useToast } from "@/components/common/toast-context"

interface SettingsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  config: AppConfig
  onSaved: (cfg: AppConfig) => void
  showPreview: boolean
  onShowPreviewChange: (v: boolean) => void
  onDownloadStatusUpdated: () => void
}

// DESIGN_SPEC §6.10 设置对话框（+ §4.1 数据维护）
export function SettingsDialog({
  open,
  onOpenChange,
  config,
  onSaved,
  showPreview,
  onShowPreviewChange,
  onDownloadStatusUpdated,
}: SettingsDialogProps) {
  const { toast } = useToast()
  const [url, setUrl] = useState(config.manual_manga_site_url ?? "")
  const [hanhuaOnly, setHanhuaOnly] = useState(config.recent_updates_hanhua_only)
  const [saving, setSaving] = useState(false)
  const [updating, setUpdating] = useState(false)

  useEffect(() => {
    if (open) {
      setUrl(config.manual_manga_site_url ?? "")
      setHanhuaOnly(config.recent_updates_hanhua_only)
    }
  }, [open, config])

  const handleSave = async () => {
    setSaving(true)
    try {
      const trimmed = url.trim()
      const cfg = await settingsApi.updateSettings({
        manual_manga_site_url: trimmed || null,
        recent_updates_hanhua_only: hanhuaOnly,
      })
      onSaved(cfg)
      toast("设置已保存")
      onOpenChange(false)
    } catch (e) {
      toast(e instanceof Error ? e.message : "保存失败")
    } finally {
      setSaving(false)
    }
  }

  const handleUpdateStatus = async () => {
    setUpdating(true)
    try {
      const res = await syncApi.updateDownloadStatus()
      if (res.success && res.data) {
        const d = res.data
        toast(`扫描 ${d.scanned_files} 个文件，已下载 ${d.marked_downloaded} 部`)
        onDownloadStatusUpdated()
      } else {
        toast(res.error || "更新失败")
      }
    } finally {
      setUpdating(false)
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 60,
            background: "rgba(0,0,0,.55)",
            backdropFilter: "blur(4px)",
            WebkitBackdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 18,
          }}
        >
          <Dialog.Content
            className="anim-popin"
            aria-describedby={undefined}
            style={{
              width: "min(440px, 100%)",
              maxHeight: "90vh",
              overflow: "auto",
              borderRadius: 18,
              background: "var(--surface)",
              border: "1px solid var(--border)",
              boxShadow: "0 30px 80px rgba(0,0,0,.5)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* 头部 */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "16px 18px",
                borderBottom: "1px solid var(--border)",
              }}
            >
              <SettingsIcon size={18} style={{ color: "var(--accent)" }} />
              <Dialog.Title style={{ fontSize: 16, fontWeight: 700, margin: 0, flex: 1 }}>
                设置
              </Dialog.Title>
              <Dialog.Close
                aria-label="关闭"
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: 8,
                  border: "none",
                  background: "var(--surface2)",
                  color: "var(--text2)",
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <X size={16} />
              </Dialog.Close>
            </div>

            {/* 本文 */}
            <div style={{ padding: 18, display: "flex", flexDirection: "column", gap: 16 }}>
              {/* 手动站点域名 */}
              <div>
                <label style={{ fontSize: 13.5, fontWeight: 500, display: "block", marginBottom: 7 }}>
                  手动站点域名
                </label>
                <input
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://example.com"
                  style={{
                    width: "100%",
                    height: 40,
                    padding: "0 12px",
                    borderRadius: 10,
                    border: "1px solid var(--border)",
                    background: "var(--surface2)",
                    color: "var(--text)",
                    fontSize: 13.5,
                    outline: "none",
                  }}
                />
                <p style={{ fontSize: 11, color: "var(--text2)", marginTop: 6, lineHeight: 1.5 }}>
                  当站点域名变化时手动指定，用于拼接漫画与封面链接。留空则使用默认。
                </p>
              </div>

              {/* 显示封面预览 */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  padding: "12px 14px",
                  borderRadius: 11,
                  background: "var(--surface2)",
                }}
              >
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13.5, fontWeight: 500 }}>显示封面预览</div>
                  <div style={{ fontSize: 11, color: "var(--text2)", marginTop: 2 }}>
                    关闭后使用渐变占位，减少图片请求。
                  </div>
                </div>
                <Switch checked={showPreview} onChange={onShowPreviewChange} />
              </div>

              {/* 仅获取「汉化」作品 */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  padding: "12px 14px",
                  borderRadius: 11,
                  background: "var(--surface2)",
                }}
              >
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13.5, fontWeight: 500 }}>最近更新仅获取「汉化」作品</div>
                  <div style={{ fontSize: 11, color: "var(--text2)", marginTop: 2 }}>
                    检索新作时，仅保留详情「分类」含「漢化」的作品。关闭则获取全部。
                  </div>
                </div>
                <Switch checked={hanhuaOnly} onChange={setHanhuaOnly} />
              </div>

              {/* §4.1 数据维护 */}
              <div
                style={{
                  padding: "12px 14px",
                  borderRadius: 11,
                  background: "var(--surface2)",
                  display: "flex",
                  flexDirection: "column",
                  gap: 10,
                }}
              >
                <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text2)" }}>数据维护</div>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13.5, fontWeight: 500 }}>更新下载状态</div>
                    <div style={{ fontSize: 11, color: "var(--text2)", marginTop: 2 }}>
                      扫描本地 CBZ 文件并同步数据库的下载状态。
                    </div>
                  </div>
                  <button
                    onClick={handleUpdateStatus}
                    disabled={updating}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 6,
                      height: 36,
                      padding: "0 13px",
                      borderRadius: 9,
                      border: "1px solid var(--border)",
                      background: "var(--surface)",
                      color: "var(--text)",
                      fontSize: 13,
                      fontWeight: 500,
                      flexShrink: 0,
                    }}
                  >
                    {updating ? <Loader2 size={15} className="anim-spin" /> : <FileCheck size={15} />}
                    {updating ? "扫描中…" : "更新"}
                  </button>
                </div>
              </div>

              {/* 保存 */}
              <button
                onClick={handleSave}
                disabled={saving}
                style={{
                  height: 44,
                  borderRadius: 11,
                  border: "none",
                  background: "var(--gradient)",
                  color: "#fff",
                  fontSize: 14,
                  fontWeight: 600,
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 7,
                }}
              >
                {saving && <Loader2 size={16} className="anim-spin" />}
                保存设置
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Overlay>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
