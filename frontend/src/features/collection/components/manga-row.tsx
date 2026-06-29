import { useState } from "react"
import { ExternalLink, Trash2, Check } from "lucide-react"
import type { MangaItem } from "@/lib/types"
import type { MangaStatus } from "../logic"
import { coverGradClass, formatDate } from "@/lib/format"

interface MangaRowProps {
  manga: MangaItem
  index: number
  status: MangaStatus
  progress: number
  selectionMode: boolean
  selected: boolean
  onToggleSelect: () => void
  onOpenOriginal: () => void
  onDownload: () => void
  onDelete: () => void
}

const STATUS_LABEL: Record<MangaStatus, { label: string; color: string }> = {
  downloaded: { label: "已下载", color: "var(--state-downloaded)" },
  downloading: { label: "下载中", color: "var(--state-downloading)" },
  pending: { label: "待下载", color: "var(--accent)" },
}

// DESIGN_SPEC §6.8 漫画行（列表视图）
export function MangaRow({
  manga,
  index,
  status,
  progress,
  selectionMode,
  selected,
  onToggleSelect,
  onOpenOriginal,
  onDownload,
  onDelete,
}: MangaRowProps) {
  const [hover, setHover] = useState(false)
  const meta = STATUS_LABEL[status]
  const date = formatDate(manga.updated_at)

  const stop = (fn: () => void) => (e: React.MouseEvent) => {
    e.stopPropagation()
    fn()
  }

  const borderColor = selected
    ? "var(--accent)"
    : hover
      ? "color-mix(in srgb, var(--accent) 50%, var(--border))"
      : "var(--border)"

  return (
    <div
      onClick={() => (selectionMode ? onToggleSelect() : onOpenOriginal())}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      className="cv-row"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 13,
        padding: "10px 13px",
        borderRadius: 12,
        background: "var(--surface)",
        border: `1px solid ${borderColor}`,
        cursor: "pointer",
        transition: "border-color .18s ease",
      }}
    >
      {selectionMode && (
        <div
          style={{
            width: 20,
            height: 20,
            flexShrink: 0,
            borderRadius: 6,
            border: "1.5px solid " + (selected ? "var(--accent)" : "var(--border)"),
            background: selected ? "var(--accent)" : "transparent",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {selected && <Check size={13} color="#fff" />}
        </div>
      )}

      {/* 迷你封面 */}
      <div
        className={coverGradClass(index)}
        style={{ width: 42, height: 56, borderRadius: 8, flexShrink: 0, overflow: "hidden" }}
      >
        {manga.preview_image_url && (
          <img
            src={manga.preview_image_url}
            alt=""
            loading="lazy"
            decoding="async"
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        )}
      </div>

      {/* 标题 / 作者 / 页数 */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontSize: 14,
            fontWeight: 600,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {manga.title}
        </div>
        <div style={{ fontSize: 12, color: "var(--text2)", marginTop: 2 }}>
          {manga.author}
          {manga.page_count != null && <span> · {manga.page_count}P</span>}
          {date && <span className="tabular"> · {date}</span>}
        </div>
      </div>

      {/* 右侧：下载中进度 / 状态 / 操作 */}
      {status === "downloading" ? (
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
          <div
            style={{ width: 90, height: 5, borderRadius: 3, background: "var(--surface2)", overflow: "hidden" }}
          >
            <div style={{ width: `${progress}%`, height: "100%", background: "var(--accent)" }} />
          </div>
          <span className="tabular" style={{ fontSize: 11.5, color: "var(--text2)", minWidth: 34 }}>
            {Math.round(progress)}%
          </span>
        </div>
      ) : status === "downloaded" ? (
        <span
          style={{
            flexShrink: 0,
            padding: "5px 12px",
            borderRadius: 7,
            fontSize: 12,
            fontWeight: 600,
            color: meta.color,
            background: "color-mix(in srgb, #22c55e 15%, transparent)",
          }}
        >
          已下载
        </span>
      ) : (
        <button
          onClick={stop(onDownload)}
          style={{
            flexShrink: 0,
            height: 32,
            padding: "0 16px",
            borderRadius: 9,
            border: "none",
            background: "var(--gradient)",
            color: "#fff",
            fontSize: 12.5,
            fontWeight: 600,
          }}
        >
          下载
        </button>
      )}

      {/* 外链 / 删除 */}
      <button onClick={stop(onOpenOriginal)} title="在原站点打开" style={rowIconBtn}>
        <ExternalLink size={15} />
      </button>
      <button onClick={stop(onDelete)} title="删除" style={rowIconBtn}>
        <Trash2 size={15} />
      </button>
    </div>
  )
}

const rowIconBtn: React.CSSProperties = {
  width: 32,
  height: 32,
  flexShrink: 0,
  borderRadius: 9,
  border: "1px solid var(--border)",
  background: "var(--surface)",
  color: "var(--text2)",
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
}
