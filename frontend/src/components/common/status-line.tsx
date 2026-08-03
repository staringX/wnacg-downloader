import { Clock, Loader2 } from "lucide-react"
import { formatDateTime } from "@/lib/format"

// 「最后更新：YYYY-MM-DD HH:mm」行（値が無ければ非表示）
export function LastUpdated({ syncedAt }: { syncedAt: string | null }) {
  const text = formatDateTime(syncedAt)
  if (!text) return null
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        fontSize: 11.5,
        color: "var(--text2)",
      }}
      className="tabular"
    >
      <Clock size={12} />
      最后更新：{text}
    </div>
  )
}

// 更新中の相互排他を伝えるバナー
export function SyncingNotice({ text }: { text: string }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "8px 12px",
        borderRadius: 10,
        fontSize: 12.5,
        color: "var(--accent-strong)",
        background: "var(--accent-soft)",
        border: "1px solid color-mix(in srgb, var(--accent) 30%, var(--border))",
      }}
    >
      <Loader2 size={14} className="anim-spin" />
      {text}
    </div>
  )
}
