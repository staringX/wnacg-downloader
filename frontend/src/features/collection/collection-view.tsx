import { useMemo, useState } from "react"
import { Search } from "lucide-react"
import type { MangaItem } from "@/lib/types"
import type { DownloadState } from "@/hooks/use-downloads"
import { StatCards } from "./components/stat-cards"
import { CollectionToolbar } from "./components/collection-toolbar"
import type { ViewMode } from "./components/collection-toolbar"
import { SelectionBar } from "./components/selection-bar"
import { MangaCard } from "./components/manga-card"
import { MangaRow } from "./components/manga-row"
import { AuthorSectionHeader } from "@/components/common/author-section-header"
import { LastUpdated, SyncingNotice } from "@/components/common/status-line"
import { coverIndexFromKey } from "@/lib/format"
import {
  filterMangas,
  filterByAuthors,
  sortByRelease,
  uniqueAuthors,
  groupByAuthor,
  statusOf,
} from "./logic"

interface CollectionViewProps {
  mangas: MangaItem[]
  downloads: Record<string, DownloadState>
  showPreview: boolean
  isSyncing: boolean
  syncDisabled: boolean
  downloadDisabled: boolean
  syncedAt: string | null
  onSync: () => void
  onDownload: (id: string) => void
  onDelete: (id: string) => void
  onBatchDelete: (ids: string[]) => void
  onDownloadAll: (ids: string[]) => void
  onOpenOriginal: (m: MangaItem) => void
}

export function CollectionView(props: CollectionViewProps) {
  const {
    mangas,
    downloads,
    showPreview,
    isSyncing,
    syncDisabled,
    downloadDisabled,
    syncedAt,
    onSync,
    onDownload,
    onDelete,
    onBatchDelete,
    onDownloadAll,
    onOpenOriginal,
  } = props

  const [search, setSearch] = useState("")
  const [view, setView] = useState<ViewMode>("card")
  const [selectedAuthors, setSelectedAuthors] = useState<Set<string>>(new Set())
  const [group, setGroup] = useState(false)
  const [selectionMode, setSelectionMode] = useState(false)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({})

  const downloaded = mangas.filter((m) => m.is_downloaded).length
  const pendingIds = useMemo(
    () => mangas.filter((m) => !m.is_downloaded && !downloads[m.id]).map((m) => m.id),
    [mangas, downloads]
  )

  const authors = useMemo(() => uniqueAuthors(mangas), [mangas])

  // 常にリリース時間の新しい順。検索＋作者マルチ選択で絞り込む。
  const visible = useMemo(() => {
    const filtered = filterByAuthors(filterMangas(mangas, search), selectedAuthors)
    return sortByRelease(filtered)
  }, [mangas, search, selectedAuthors])

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const exitSelection = () => {
    setSelectionMode(false)
    setSelected(new Set())
  }

  const handleBatchDelete = () => {
    onBatchDelete(Array.from(selected))
    exitSelection()
  }

  const renderItem = (m: MangaItem) => {
    const status = statusOf(m, downloads)
    const progress = downloads[m.id]?.progress ?? 0
    const common = {
      manga: m,
      index: coverIndexFromKey(m.id),
      status,
      progress,
      selectionMode,
      selected: selected.has(m.id),
      onToggleSelect: () => toggleSelect(m.id),
      onOpenOriginal: () => onOpenOriginal(m),
      onDownload: () => onDownload(m.id),
      onDelete: () => onDelete(m.id),
    }
    return view === "card" ? (
      <MangaCard key={m.id} showPreview={showPreview} downloadDisabled={downloadDisabled} {...common} />
    ) : (
      <MangaRow key={m.id} downloadDisabled={downloadDisabled} {...common} />
    )
  }

  const gridStyle: React.CSSProperties =
    view === "card"
      ? {
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(168px, 1fr))",
          gap: 16,
        }
      : { display: "flex", flexDirection: "column", gap: 8 }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      <StatCards total={mangas.length} downloaded={downloaded} pending={pendingIds.length} />

      <CollectionToolbar
        search={search}
        onSearch={setSearch}
        view={view}
        onViewChange={setView}
        authors={authors}
        selectedAuthors={selectedAuthors}
        onAuthorsChange={setSelectedAuthors}
        groupByAuthor={group}
        onToggleGroup={() => setGroup((g) => !g)}
        selectionMode={selectionMode}
        onToggleSelection={() => (selectionMode ? exitSelection() : setSelectionMode(true))}
        onSync={onSync}
        isSyncing={isSyncing}
        syncDisabled={syncDisabled}
        downloadDisabled={downloadDisabled}
        onDownloadAll={() => onDownloadAll(pendingIds)}
        pendingCount={pendingIds.length}
      />

      <LastUpdated syncedAt={syncedAt} />
      {isSyncing && <SyncingNotice text="正在更新收藏夹，其它操作已暂停…" />}

      {selectionMode && (
        <SelectionBar count={selected.size} onDelete={handleBatchDelete} onCancel={exitSelection} />
      )}

      {visible.length === 0 ? (
        <EmptyState />
      ) : group ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
          {groupByAuthor(visible).map((g) => {
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
                  <div style={gridStyle}>
                    {g.mangas.map((m) => renderItem(m))}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      ) : (
        <div style={gridStyle}>{visible.map((m) => renderItem(m))}</div>
      )}
    </div>
  )
}

function EmptyState() {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 12,
        padding: "80px 0",
        color: "var(--text2)",
      }}
    >
      <Search size={40} />
      <span style={{ fontSize: 14 }}>没有匹配的漫画</span>
    </div>
  )
}
