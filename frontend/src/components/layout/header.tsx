import { Library, Clock, ExternalLink, Sun, Moon, Settings, Menu } from "lucide-react"
import { useTheme } from "@/components/common/theme-context"
import { openKomga } from "@/lib/komga"

export type TabKey = "collection" | "updates"

interface HeaderProps {
  currentTab: TabKey
  onTabChange: (tab: TabKey) => void
  updatesCount: number
  isMobile: boolean
  onOpenSettings: () => void
  onToggleMobileMenu: () => void
}

const iconBtn: React.CSSProperties = {
  width: 38,
  height: 38,
  borderRadius: 10,
  border: "1px solid var(--border)",
  background: "var(--surface2)",
  color: "var(--text2)",
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
}

export function Header({
  currentTab,
  onTabChange,
  updatesCount,
  isMobile,
  onOpenSettings,
  onToggleMobileMenu,
}: HeaderProps) {
  const { theme, toggleTheme } = useTheme()

  const renderTab = (key: TabKey, label: string, Icon: typeof Library, count?: number) => {
    const active = currentTab === key
    return (
      <button
        onClick={() => onTabChange(key)}
        aria-current={active ? "page" : undefined}
        style={{
          height: 38,
          padding: "0 15px",
          borderRadius: 10,
          border: "none",
          display: "inline-flex",
          alignItems: "center",
          gap: 7,
          background: active ? "color-mix(in srgb, var(--accent) 16%, transparent)" : "transparent",
          color: active ? "var(--accent-strong)" : "var(--text2)",
          fontSize: 14,
          fontWeight: active ? 600 : 500,
        }}
      >
        <Icon size={16} />
        {label}
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
    <header
      style={{
        position: "sticky",
        top: 0,
        zIndex: 40,
        height: 64,
        borderBottom: "1px solid var(--border)",
        background: "var(--header-bg)",
        backdropFilter: "blur(18px)",
        WebkitBackdropFilter: "blur(18px)",
      }}
    >
      <div
        style={{
          maxWidth: 1480,
          height: "100%",
          margin: "0 auto",
          padding: "0 clamp(14px, 3vw, 28px)",
          display: "flex",
          alignItems: "center",
          gap: 18,
        }}
      >
        {/* 品牌 */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexShrink: 0 }}>
          <div
            style={{
              width: 38,
              height: 38,
              borderRadius: 11,
              background: "var(--gradient)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 6px 18px color-mix(in srgb, var(--accent) 45%, transparent)",
            }}
          >
            <Library size={20} color="#fff" />
          </div>
          {!isMobile && (
            <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.1 }}>
              <span
                className="font-display"
                style={{ fontSize: 16, fontWeight: 700, letterSpacing: "-0.01em" }}
              >
                MangaVault
              </span>
              <span
                style={{ fontSize: 10.5, color: "var(--text2)", letterSpacing: "0.04em" }}
              >
                漫画下载管理
              </span>
            </div>
          )}
        </div>

        <div style={{ flex: 1 }} />

        {isMobile ? (
          <button onClick={onToggleMobileMenu} style={{ ...iconBtn, width: 40, height: 40 }} aria-label="菜单">
            <Menu size={20} />
          </button>
        ) : (
          <>
            {/* 标签 */}
            <nav style={{ display: "flex", gap: 4 }}>
              {renderTab("collection", "收藏夹", Library)}
              {renderTab("updates", "最近更新", Clock, updatesCount)}
            </nav>

            {/* 操作 */}
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <button
                onClick={openKomga}
                style={{
                  height: 38,
                  padding: "0 14px",
                  borderRadius: 10,
                  border: "1px solid var(--border)",
                  background: "var(--surface2)",
                  color: "var(--text2)",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 7,
                  fontSize: 13.5,
                  fontWeight: 500,
                }}
              >
                <ExternalLink size={16} />
                Komga
              </button>
              <button onClick={toggleTheme} style={iconBtn} aria-label="切换主题">
                {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
              </button>
              <button onClick={onOpenSettings} style={iconBtn} aria-label="设置">
                <Settings size={18} />
              </button>
            </div>
          </>
        )}
      </div>
    </header>
  )
}
