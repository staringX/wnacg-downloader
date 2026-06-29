import { useMemo, useState } from "react"
import { Zap, Users, Search, Clock } from "lucide-react"
import type { RecentUpdate } from "@/lib/types"
import type { DownloadState } from "@/hooks/use-downloads"
import { RecentUpdateCard } from "./components/recent-update-card"
import { AuthorSectionHeader } from "@/components/common/author-section-header"
import { groupByAuthor } from "@/features/collection/logic"

interface RecentViewProps {
  updates: RecentUpdate[]
  downloads: Record<string, DownloadState>
  showPreview: boolean
  isSyncing: boolean
  onSync: () => void
  onDownload: (id: string) => void
  onToggleFavorite: (u: RecentUpdate) => void
  onOpenOriginal: (u: RecentUpdate) => void
}

export function RecentView(props: RecentViewProps) {
  const { updates, downloads, showPreview, isSyncing, onSync, onDownload, onToggleFavorite, onOpenOriginal } =
    props
  const [group, setGroup] = useState(false)
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({})

  const grid: React.CSSProperties = {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
    gap: 14,
  }

  const renderCard = (u: RecentUpdate, index: number) => {
    const dl = downloads[u.id]
    return (
      <RecentUpdateCard
        key={u.id}
        update={u}
        index={index}
        showPreview={showPreview}
        downloading={Boolean(dl)}
        progress={dl?.progress ?? 0}
        onOpenOriginal={() => onOpenOriginal(u)}
        onToggleFavorite={() => onToggleFavorite(u)}
        onDownload={() => onDownload(u.id)}
      />
    )
  }

  const groups = useMemo(() => groupByAuthor(updates), [updates])

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      {/* 告知バー */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: 12,
          padding: "14px 16px",
          borderRadius: 14,
          background: "linear-gradient(120deg, color-mix(in srgb, var(--accent) 16%, var(--surface)), var(--surface))",
          border: "1px solid color-mix(in srgb, var(--accent) 30%, var(--border))",
        }}
      >
        <Zap size={20} style={{ color: "var(--accent)", flexShrink: 0 }} />
        <div style={{ flex: "1 1 200px", minWidth: 0 }}>
          <div style={{ fontSize: 14, fontWeight: 600 }}>关注作者的新作品</div>
          <div style={{ fontSize: 12, color: "var(--text2)", marginTop: 2 }}>
            检索收藏作者的最新更新，一键收藏或下载。
          </div>
        </div>
        <button
          onClick={() => setGroup((g) => !g)}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 7,
            height: 36,
            padding: "0 13px",
            borderRadius: 10,
            fontSize: 13,
            fontWeight: 500,
            border: `1px solid ${group ? "var(--accent)" : "var(--border)"}`,
            background: group ? "var(--accent-soft)" : "var(--surface)",
            color: group ? "var(--accent)" : "var(--text)",
          }}
        >
          <Users size={15} />
          按作者分组
        </button>
        <button
          onClick={onSync}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 7,
            height: 36,
            padding: "0 15px",
            borderRadius: 10,
            border: "none",
            background: "var(--gradient)",
            color: "#fff",
            fontSize: 13,
            fontWeight: 600,
            boxShadow: "0 6px 16px color-mix(in srgb, var(--accent) 40%, transparent)",
          }}
        >
          <Search size={15} className={isSyncing ? "anim-spin" : undefined} />
          检索新作
        </button>
      </div>

      {updates.length === 0 ? (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 12,
            padding: "80px 0",
            color: "var(--text2)",
          }}
        >
          <Clock size={40} />
          <span style={{ fontSize: 14 }}>暂无最近更新，点击「检索新作」获取</span>
        </div>
      ) : group ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
          {groups.map((g) => {
            const isCollapsed = collapsed[g.author]
            return (
              <div key={g.author}>
                <AuthorSectionHeader
                  author={g.author}
                  count={g.mangas.length}
                  collapsed={isCollapsed}
                  onToggle={() =>
                    setCollapsed((prev) => ({ ...prev, [g.author]: !prev[g.author] }))
                  }
                />
                {!isCollapsed && (
                  <div style={grid}>
                    {g.mangas.map((m) =>
                      renderCard(m as RecentUpdate, updates.indexOf(m as RecentUpdate))
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      ) : (
        <div style={grid}>{updates.map((u, i) => renderCard(u, i))}</div>
      )}
    </div>
  )
}
