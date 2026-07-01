import { useMemo, useState } from "react"
import { Zap, Users, Search, Clock } from "lucide-react"
import type { RecentUpdate } from "@/lib/types"
import type { DownloadState } from "@/hooks/use-downloads"
import { RecentUpdateCard } from "./components/recent-update-card"
import { AuthorSectionHeader } from "@/components/common/author-section-header"
import { AuthorFilter } from "@/components/common/author-filter"
import { LastUpdated, SyncingNotice } from "@/components/common/status-line"
import { groupByAuthor, filterByAuthors, uniqueAuthors } from "@/features/collection/logic"

interface RecentViewProps {
  updates: RecentUpdate[]
  downloads: Record<string, DownloadState>
  showPreview: boolean
  isSyncing: boolean
  syncDisabled: boolean
  downloadDisabled: boolean
  syncedAt: string | null
  onSync: () => void
  onDownload: (id: string) => void
  onToggleFavorite: (u: RecentUpdate) => void
  onOpenOriginal: (u: RecentUpdate) => void
}

export function RecentView(props: RecentViewProps) {
  const {
    updates,
    downloads,
    showPreview,
    isSyncing,
    syncDisabled,
    downloadDisabled,
    syncedAt,
    onSync,
    onDownload,
    onToggleFavorite,
    onOpenOriginal,
  } = props
  const [group, setGroup] = useState(false)
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({})
  const [selectedAuthors, setSelectedAuthors] = useState<Set<string>>(new Set())

  const authors = useMemo(() => uniqueAuthors(updates), [updates])
  const visible = useMemo(() => filterByAuthors(updates, selectedAuthors), [updates, selectedAuthors])

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
        downloadDisabled={downloadDisabled}
        onOpenOriginal={() => onOpenOriginal(u)}
        onToggleFavorite={() => onToggleFavorite(u)}
        onDownload={() => onDownload(u.id)}
      />
    )
  }

  const groups = useMemo(() => groupByAuthor(visible), [visible])

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
        <AuthorFilter authors={authors} selected={selectedAuthors} onChange={setSelectedAuthors} />
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
          disabled={syncDisabled}
          title={syncDisabled ? "下载或更新进行中，暂不可检索" : undefined}
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
            opacity: syncDisabled ? 0.5 : 1,
            cursor: syncDisabled ? "not-allowed" : "pointer",
            boxShadow: "0 6px 16px color-mix(in srgb, var(--accent) 40%, transparent)",
          }}
        >
          <Search size={15} className={isSyncing ? "anim-spin" : undefined} />
          检索新作
        </button>
      </div>

      <LastUpdated syncedAt={syncedAt} />
      {isSyncing && <SyncingNotice text="正在检索新作，其它操作已暂停…" />}

      {visible.length === 0 ? (
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
          <span style={{ fontSize: 14 }}>
            {updates.length === 0 ? "暂无最近更新，点击「检索新作」获取" : "没有匹配的作者"}
          </span>
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
                      renderCard(m as RecentUpdate, visible.indexOf(m as RecentUpdate))
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      ) : (
        <div style={grid}>{visible.map((u, i) => renderCard(u, i))}</div>
      )}
    </div>
  )
}
