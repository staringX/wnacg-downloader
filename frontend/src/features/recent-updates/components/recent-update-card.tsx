import { useState } from "react"
import { Heart, FileText, Calendar, Loader2 } from "lucide-react"
import type { RecentUpdate } from "@/lib/types"
import { coverGradClass, formatDate } from "@/lib/format"

interface Props {
  update: RecentUpdate
  index: number
  showPreview: boolean
  downloading: boolean
  progress: number
  downloadDisabled: boolean
  onOpenOriginal: () => void
  onToggleFavorite: () => void
  onDownload: () => void
}

// DESIGN_SPEC §6.9 最近更新卡片
export function RecentUpdateCard({
  update,
  index,
  showPreview,
  downloading,
  progress,
  downloadDisabled,
  onOpenOriginal,
  onToggleFavorite,
  onDownload,
}: Props) {
  const [hover, setHover] = useState(false)
  const favorited = Boolean(update.is_favorited)
  const downloaded = Boolean(update.is_downloaded)
  const date = formatDate(update.updated_at)
  const hasPreview = showPreview && Boolean(update.preview_image_url)

  const stop = (fn: () => void) => (e: React.MouseEvent) => {
    e.stopPropagation()
    fn()
  }

  return (
    <div
      onClick={onOpenOriginal}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      className="cv-recent"
      style={{
        display: "flex",
        gap: 12,
        padding: 12,
        borderRadius: 14,
        background: "var(--surface)",
        cursor: "pointer",
        border: `1px solid ${hover ? "color-mix(in srgb, var(--accent) 45%, var(--border))" : "var(--border)"}`,
        transition: "border-color .18s ease",
      }}
    >
      {/* 封面 */}
      <div
        className={hasPreview ? undefined : coverGradClass(index)}
        style={{
          position: "relative",
          width: 74,
          height: 100,
          flexShrink: 0,
          borderRadius: 10,
          overflow: "hidden",
        }}
      >
        {hasPreview && (
          <img
            src={update.preview_image_url as string}
            alt={update.title}
            loading="lazy"
            decoding="async"
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        )}
        <span
          style={{
            position: "absolute",
            top: 6,
            left: 6,
            padding: "2px 6px",
            borderRadius: 6,
            background: "var(--accent)",
            color: "#fff",
            fontSize: 9.5,
            fontWeight: 700,
          }}
        >
          NEW
        </span>
      </div>

      {/* 右侧 */}
      <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
        <div
          style={{
            fontSize: 13.5,
            fontWeight: 600,
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
          }}
        >
          {update.title}
        </div>
        <div style={{ fontSize: 11.5, color: "var(--text2)", marginTop: 2 }}>{update.author}</div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            marginTop: 5,
            fontSize: 11,
            color: "var(--text2)",
          }}
        >
          {date && (
            <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }} className="tabular">
              <Calendar size={11} />
              {date}
            </span>
          )}
          {update.page_count != null && (
            <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
              <FileText size={11} />
              {update.page_count}P
            </span>
          )}
        </div>

        <div style={{ flex: 1 }} />

        {/* 操作行 */}
        <div style={{ display: "flex", alignItems: "center", gap: 7, marginTop: 8 }}>
          <button
            onClick={stop(onToggleFavorite)}
            title="收藏到网站"
            style={{
              width: 36,
              height: 34,
              borderRadius: 9,
              flexShrink: 0,
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              border: `1px solid ${favorited ? "var(--accent)" : "var(--border)"}`,
              background: favorited ? "var(--accent-soft)" : "var(--surface)",
              color: favorited ? "var(--accent)" : "var(--text2)",
            }}
          >
            <Heart size={16} fill={favorited ? "var(--accent)" : "none"} />
          </button>

          <button
            onClick={stop(onDownload)}
            disabled={downloading || downloaded || downloadDisabled}
            title={downloadDisabled && !downloading && !downloaded ? "更新进行中，暂不可下载" : undefined}
            style={{
              flex: 1,
              height: 34,
              borderRadius: 9,
              border: "none",
              fontSize: 12.5,
              fontWeight: 600,
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 6,
              background: downloading || downloaded ? "var(--surface2)" : "var(--gradient)",
              color: downloading || downloaded ? "var(--text2)" : "#fff",
              opacity: downloadDisabled && !downloading && !downloaded ? 0.5 : 1,
              cursor: downloadDisabled && !downloading && !downloaded ? "not-allowed" : "pointer",
            }}
          >
            {downloading ? (
              <>
                <Loader2 size={14} className="anim-spin" />
                <span className="tabular">{Math.round(progress)}%</span>
              </>
            ) : downloaded ? (
              "已加入"
            ) : (
              "下载"
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
