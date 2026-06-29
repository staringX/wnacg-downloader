import { Search, LayoutGrid, List, ChevronDown, Users, CheckSquare, RefreshCw, Download } from "lucide-react"
import type { SortMode } from "../logic"
import { SORT_OPTIONS } from "../logic"

export type ViewMode = "card" | "list"

interface ToolbarProps {
  search: string
  onSearch: (v: string) => void
  view: ViewMode
  onViewChange: (v: ViewMode) => void
  sort: SortMode
  onSortChange: (v: SortMode) => void
  groupByAuthor: boolean
  onToggleGroup: () => void
  selectionMode: boolean
  onToggleSelection: () => void
  onSync: () => void
  isSyncing: boolean
  onDownloadAll: () => void
  pendingCount: number
}

const toolBtn: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 7,
  height: 40,
  padding: "0 14px",
  borderRadius: 11,
  fontSize: 13.5,
  fontWeight: 500,
  border: "1px solid var(--border)",
  background: "var(--surface)",
  color: "var(--text)",
}

function activeToggleStyle(on: boolean): React.CSSProperties {
  return on
    ? {
        ...toolBtn,
        border: "1px solid var(--accent)",
        background: "var(--accent-soft)",
        color: "var(--accent)",
      }
    : toolBtn
}

// DESIGN_SPEC §6.4 工具栏（仅收藏夹标签）
export function CollectionToolbar(props: ToolbarProps) {
  const {
    search,
    onSearch,
    view,
    onViewChange,
    sort,
    onSortChange,
    groupByAuthor,
    onToggleGroup,
    selectionMode,
    onToggleSelection,
    onSync,
    isSyncing,
    onDownloadAll,
    pendingCount,
  } = props

  const segBtn = (mode: ViewMode, Icon: typeof LayoutGrid) => {
    const active = view === mode
    return (
      <button
        onClick={() => onViewChange(mode)}
        style={{
          width: 34,
          height: 30,
          borderRadius: 8,
          border: "none",
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          background: active ? "var(--accent)" : "transparent",
          color: active ? "#fff" : "var(--text2)",
        }}
        aria-label={mode === "card" ? "卡片视图" : "列表视图"}
      >
        <Icon size={16} />
      </button>
    )
  }

  return (
    <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 10 }}>
      {/* 搜索 */}
      <div style={{ position: "relative", flex: "1 1 220px", minWidth: 180 }}>
        <Search
          size={16}
          style={{
            position: "absolute",
            left: 13,
            top: "50%",
            transform: "translateY(-50%)",
            color: "var(--text2)",
            pointerEvents: "none",
          }}
        />
        <input
          value={search}
          onChange={(e) => onSearch(e.target.value)}
          placeholder="搜索标题或作者…"
          style={{
            width: "100%",
            height: 40,
            padding: "0 14px 0 38px",
            borderRadius: 11,
            border: "1px solid var(--border)",
            background: "var(--surface)",
            color: "var(--text)",
            fontSize: 13.5,
            outline: "none",
          }}
          onFocus={(e) => (e.currentTarget.style.borderColor = "var(--accent)")}
          onBlur={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
        />
      </div>

      {/* 卡片/列表切换 */}
      <div
        style={{
          display: "inline-flex",
          gap: 0,
          padding: 3,
          borderRadius: 11,
          border: "1px solid var(--border)",
          background: "var(--surface)",
        }}
      >
        {segBtn("card", LayoutGrid)}
        {segBtn("list", List)}
      </div>

      {/* 排序 */}
      <div style={{ position: "relative" }}>
        <select
          value={sort}
          onChange={(e) => onSortChange(e.target.value as SortMode)}
          style={{
            height: 40,
            padding: "0 34px 0 13px",
            borderRadius: 11,
            border: "1px solid var(--border)",
            background: "var(--surface)",
            color: "var(--text)",
            fontSize: 13.5,
            appearance: "none",
            WebkitAppearance: "none",
            outline: "none",
          }}
        >
          {SORT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <ChevronDown
          size={14}
          style={{
            position: "absolute",
            right: 12,
            top: "50%",
            transform: "translateY(-50%)",
            color: "var(--text2)",
            pointerEvents: "none",
          }}
        />
      </div>

      {/* 按作者分组 */}
      <button style={activeToggleStyle(groupByAuthor)} onClick={onToggleGroup}>
        <Users size={16} />
        按作者分组
      </button>

      {/* 选择 */}
      <button style={activeToggleStyle(selectionMode)} onClick={onToggleSelection}>
        <CheckSquare size={16} />
        {selectionMode ? "退出选择" : "选择"}
      </button>

      {/* 同步 */}
      <button style={toolBtn} onClick={onSync}>
        <RefreshCw size={16} className={isSyncing ? "anim-spin" : undefined} />
        同步
      </button>

      {/* 下载全部 */}
      <button
        onClick={onDownloadAll}
        disabled={pendingCount === 0}
        style={{
          ...toolBtn,
          border: "none",
          background: "var(--gradient)",
          color: "#fff",
          fontWeight: 600,
          opacity: pendingCount === 0 ? 0.5 : 1,
          boxShadow: "0 6px 16px color-mix(in srgb, var(--accent) 40%, transparent)",
        }}
      >
        <Download size={16} />
        下载全部
        <span
          className="tabular"
          style={{
            fontSize: 12,
            fontWeight: 700,
            padding: "1px 7px",
            borderRadius: 20,
            background: "rgba(255,255,255,.25)",
          }}
        >
          {pendingCount}
        </span>
      </button>
    </div>
  )
}
