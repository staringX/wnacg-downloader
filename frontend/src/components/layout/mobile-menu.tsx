import { useEffect } from "react"
import { Library, Clock, ExternalLink, Sun, Moon, Settings } from "lucide-react"
import { useTheme } from "@/components/common/theme-context"
import { openKomga } from "@/lib/komga"
import type { TabKey } from "./header"

interface MobileMenuProps {
  open: boolean
  onClose: () => void
  currentTab: TabKey
  onTabChange: (tab: TabKey) => void
  updatesCount: number
  onOpenSettings: () => void
}

const itemStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 10,
  width: "100%",
  padding: "11px 14px",
  borderRadius: 9,
  border: "none",
  background: "transparent",
  color: "var(--text)",
  fontSize: 14,
  textAlign: "left",
}

// DESIGN_SPEC §6.14 移动端下拉菜单
export function MobileMenu({
  open,
  onClose,
  currentTab,
  onTabChange,
  updatesCount,
  onOpenSettings,
}: MobileMenuProps) {
  const { theme, toggleTheme } = useTheme()

  // Esc で閉じられるようにする（モーダル的な要素の基本操作）
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose()
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [open, onClose])

  if (!open) return null

  const tab = (key: TabKey, label: string, Icon: typeof Library, count?: number) => {
    const active = currentTab === key
    return (
      <button
        style={{
          ...itemStyle,
          background: active ? "color-mix(in srgb, var(--accent) 16%, transparent)" : "transparent",
          color: active ? "var(--accent-strong)" : "var(--text)",
          fontWeight: active ? 600 : 400,
        }}
        onClick={() => {
          onTabChange(key)
          onClose()
        }}
      >
        <Icon size={18} />
        <span style={{ flex: 1 }}>{label}</span>
        {count !== undefined && (
          <span
            className="tabular"
            style={{
              fontSize: 10.5,
              fontWeight: 700,
              padding: "1px 6px",
              borderRadius: 20,
              background: active ? "var(--accent-solid)" : "var(--surface2)",
              color: active ? "#fff" : "var(--text2)",
            }}
          >
            {count}
          </span>
        )}
      </button>
    )
  }

  return (
    <>
      <div style={{ position: "fixed", inset: 0, zIndex: 38 }} onClick={onClose} />
      <div
        className="anim-slideup"
        style={{
          position: "fixed",
          top: 64,
          left: 10,
          right: 10,
          zIndex: 39,
          borderRadius: 14,
          background: "var(--surface)",
          border: "1px solid var(--border)",
          boxShadow: "0 20px 50px rgba(0,0,0,.4)",
          padding: 8,
        }}
      >
        {tab("collection", "收藏夹", Library)}
        {tab("updates", "最近更新", Clock, updatesCount)}
        <div style={{ height: 1, background: "var(--border)", margin: "8px 6px" }} />
        <button
          style={itemStyle}
          onClick={() => {
            openKomga()
            onClose()
          }}
        >
          <ExternalLink size={18} />
          Komga
        </button>
        <button style={itemStyle} onClick={toggleTheme}>
          {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
          <span style={{ flex: 1 }}>{theme === "dark" ? "切换到亮色" : "切换到暗色"}</span>
        </button>
        <button
          style={itemStyle}
          onClick={() => {
            onOpenSettings()
            onClose()
          }}
        >
          <Settings size={18} />
          设置
        </button>
      </div>
    </>
  )
}
