import { useState } from "react"
import { Loader2, FileText, ExternalLink, Trash2, Check, Download } from "lucide-react"
import type { MangaItem } from "@/lib/types"
import type { MangaStatus } from "../logic"
import { coverGradClass, formatDate, categoryTags } from "@/lib/format"
import { CategoryTags } from "@/components/common/category-tags"

interface MangaCardProps {
  manga: MangaItem
  index: number
  status: MangaStatus
  progress: number
  showPreview: boolean
  selectionMode: boolean
  selected: boolean
  downloadDisabled: boolean
  onToggleSelect: () => void
  onOpenOriginal: () => void
  onDownload: () => void
  onDelete: () => void
}

const STATUS_BADGE: Record<MangaStatus, { label: string; color: string }> = {
  downloaded: { label: "已下载", color: "var(--state-downloaded-solid)" },
  downloading: { label: "下载中", color: "var(--state-downloading-solid)" },
  pending: { label: "待下载", color: "var(--accent-solid)" },
}

// DESIGN_SPEC §6.7 漫画卡片（卡片视图）
// showPreview=true: 3/4 封面 + 覆盖层；showPreview=false: 紧凑模式（小色块 + 标题，无封面）
export function MangaCard({
  manga,
  index,
  status,
  progress,
  showPreview,
  selectionMode,
  selected,
  downloadDisabled,
  onToggleSelect,
  onOpenOriginal,
  onDownload,
  onDelete,
}: MangaCardProps) {
  const [hover, setHover] = useState(false)
  const badge = STATUS_BADGE[status]
  const date = formatDate(manga.updated_at)
  const tags = categoryTags(manga.category)
  const showCover = showPreview
  const hasImage = showCover && Boolean(manga.preview_image_url)

  const handleCardClick = () => {
    if (selectionMode) onToggleSelect()
    else onOpenOriginal()
  }

  const stop = (fn: () => void) => (e: React.MouseEvent) => {
    e.stopPropagation()
    fn()
  }

  const borderColor = selected
    ? "var(--accent)"
    : hover
      ? "color-mix(in srgb, var(--accent) 55%, var(--border))"
      : "var(--border)"

  return (
    <div
      onClick={handleCardClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      className={showCover ? "cv-card" : "cv-card-compact"}
      style={{
        cursor: "pointer",
        borderRadius: 14,
        background: "var(--surface)",
        border: `1px solid ${borderColor}`,
        overflow: "hidden",
        boxShadow: selected ? "0 0 0 2px var(--accent)" : "none",
        transform: hover ? "translateY(-4px)" : "none",
        transition: "transform .18s ease, border-color .18s ease",
      }}
    >
      {/* 封面（仅在显示封面预览时） */}
      {showCover && (
        <div
          className={hasImage ? undefined : coverGradClass(index)}
          style={{
            position: "relative",
            aspectRatio: "3 / 4",
            borderTopLeftRadius: 13,
            borderTopRightRadius: 13,
            overflow: "hidden",
          }}
        >
          {hasImage && (
            <img
              src={manga.preview_image_url as string}
              alt={manga.title}
              loading="lazy"
              decoding="async"
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          )}

          {/* 文字可读化遮罩 */}
          <div style={{ position: "absolute", inset: 0, background: "var(--cover-scrim)" }} />

          {/* 状态徽章 / 选择勾选 */}
          {selectionMode ? (
            <div
              style={{
                position: "absolute",
                top: 9,
                left: 9,
                width: 24,
                height: 24,
                borderRadius: 7,
                border: "1.5px solid #fff",
                background: selected ? "var(--accent-solid)" : "rgba(0,0,0,.5)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              {selected && <Check size={14} color="#fff" />}
            </div>
          ) : (
            <span
              style={{
                position: "absolute",
                top: 8,
                left: 8,
                padding: "3px 8px",
                borderRadius: 7,
                fontSize: 10,
                fontWeight: 700,
                color: "#fff",
                background: badge.color,
                boxShadow: "0 2px 6px rgba(0,0,0,.3)",
              }}
            >
              {badge.label}
            </span>
          )}

          {/* 页数 chip */}
          {manga.page_count != null && (
            <span
              style={{
                position: "absolute",
                top: 8,
                right: 8,
                display: "inline-flex",
                alignItems: "center",
                gap: 3,
                padding: "3px 7px",
                borderRadius: 7,
                fontSize: 10.5,
                fontWeight: 600,
                color: "#fff",
                background: "rgba(0,0,0,.5)",
                backdropFilter: "blur(4px)",
                WebkitBackdropFilter: "blur(4px)",
              }}
            >
              <FileText size={11} />
              {manga.page_count}P
            </span>
          )}

          {/* 标题 */}
          <div
            style={{
              position: "absolute",
              left: 10,
              right: 10,
              bottom: 9,
              fontSize: 13,
              fontWeight: 700,
              color: "#fff",
              textShadow: "0 1px 4px rgba(0,0,0,.5)",
              display: "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
              overflow: "hidden",
            }}
          >
            {manga.title}
          </div>

          {/* 下载中遮罩 */}
          {status === "downloading" && (
            <div
              style={{
                position: "absolute",
                inset: 0,
                background: "rgba(0,0,0,.6)",
                backdropFilter: "blur(2px)",
                WebkitBackdropFilter: "blur(2px)",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                gap: 10,
              }}
            >
              <Loader2 size={26} color="#fff" className="anim-spin" />
              <span className="tabular" style={{ fontSize: 12, fontWeight: 600, color: "#fff" }}>
                {Math.round(progress)}%
              </span>
              <div
                style={{
                  width: "70%",
                  height: 4,
                  borderRadius: 2,
                  background: "rgba(255,255,255,.25)",
                  overflow: "hidden",
                }}
              >
                <div style={{ width: `${progress}%`, height: "100%", background: "var(--accent)" }} />
              </div>
            </div>
          )}
        </div>
      )}

      {/* 底部 */}
      <div style={{ padding: showCover ? "9px 11px 11px" : "11px 12px 12px" }}>
        {/* 紧凑模式头部：色块 + 标题（无封面时） */}
        {!showCover && (
          <div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 8 }}>
            {selectionMode && (
              <div
                style={{
                  width: 24,
                  height: 24,
                  flexShrink: 0,
                  borderRadius: 7,
                  border: `1.5px solid ${selected ? "var(--accent)" : "var(--border)"}`,
                  background: selected ? "var(--accent-solid)" : "transparent",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                {selected && <Check size={14} color="#fff" />}
              </div>
            )}
            <div
              className={coverGradClass(index)}
              style={{ width: 30, height: 40, borderRadius: 7, flexShrink: 0 }}
            />
            <div
              style={{
                flex: 1,
                minWidth: 0,
                fontSize: 13.5,
                fontWeight: 700,
                lineHeight: 1.25,
                display: "-webkit-box",
                WebkitLineClamp: 2,
                WebkitBoxOrient: "vertical",
                overflow: "hidden",
              }}
            >
              {manga.title}
            </div>
          </div>
        )}

        {/* 元信息行：封面模式=作者，紧凑模式=作者 · 页数 */}
        <div
          style={{
            fontSize: 11.5,
            color: "var(--text2)",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {showCover ? manga.author : `${manga.author}${manga.page_count != null ? ` · ${manga.page_count}P` : ""}`}
        </div>
        {date && (
          <div className="tabular" style={{ fontSize: 11, color: "var(--text2)", marginTop: 2 }}>
            {date}
          </div>
        )}

        {/* 分類タグ（スラッシュ区切り） */}
        {tags.length > 0 && <CategoryTags tags={tags} style={{ marginTop: 7 }} />}

        {/* 操作行 */}
        <div style={{ display: "flex", alignItems: "center", gap: 7, marginTop: showCover ? 9 : 10 }}>
          <MainButton
            status={status}
            progress={progress}
            downloadDisabled={downloadDisabled}
            onDownload={stop(onDownload)}
          />
          <button
            onClick={stop(onOpenOriginal)}
            title="在原站点打开"
            aria-label={`在原站点打开：${manga.title}`}
            className="touch-icon-btn"
            style={ghostIconBtn}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "var(--accent)"
              e.currentTarget.style.color = "var(--accent-strong)"
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "var(--border)"
              e.currentTarget.style.color = "var(--text2)"
            }}
          >
            <ExternalLink size={15} />
          </button>
          <button
            onClick={stop(onDelete)}
            title="删除"
            aria-label={`删除：${manga.title}`}
            className="touch-icon-btn"
            style={ghostIconBtn}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "var(--danger)"
              e.currentTarget.style.color = "var(--danger-strong)"
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "var(--border)"
              e.currentTarget.style.color = "var(--text2)"
            }}
          >
            <Trash2 size={15} />
          </button>
        </div>
      </div>
    </div>
  )
}

const ghostIconBtn: React.CSSProperties = {
  width: 32,
  height: 32,
  flexShrink: 0,
  borderRadius: 9,
  border: "1px solid var(--border)",
  background: "transparent",
  color: "var(--text2)",
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
}

function MainButton({
  status,
  progress,
  downloadDisabled,
  onDownload,
}: {
  status: MangaStatus
  progress: number
  downloadDisabled: boolean
  onDownload: (e: React.MouseEvent) => void
}) {
  const base: React.CSSProperties = {
    flex: 1,
    minWidth: 0,
    height: 34,
    borderRadius: 9,
    fontSize: 12.5,
    fontWeight: 600,
    border: "none",
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
  }

  if (status === "downloaded") {
    return (
      <div
        style={{
          ...base,
          cursor: "default",
          background: "color-mix(in srgb, #22c55e 14%, var(--surface2))",
          color: "var(--success-strong)",
        }}
      >
        <Check size={15} />
        已下载
      </div>
    )
  }
  if (status === "downloading") {
    return (
      <div
        className="tabular"
        style={{ ...base, cursor: "default", background: "var(--surface2)", color: "var(--text2)" }}
      >
        下载中 {Math.round(progress)}%
      </div>
    )
  }
  return (
    <button
      onClick={onDownload}
      disabled={downloadDisabled}
      className="touch-btn"
      title={downloadDisabled ? "更新进行中，暂不可下载" : undefined}
      style={{
        ...base,
        background: "var(--gradient)",
        color: "#fff",
        opacity: downloadDisabled ? 0.5 : 1,
        cursor: downloadDisabled ? "not-allowed" : "pointer",
      }}
    >
      <Download size={15} />
      下载
    </button>
  )
}
