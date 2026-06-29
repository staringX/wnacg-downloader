import { Loader2 } from "lucide-react"
import type { SyncStrip } from "@/hooks/use-sync"

// DESIGN_SPEC §6.2 同步进度条
export function SyncProgressStrip({ strip }: { strip: SyncStrip }) {
  if (!strip.active) return null
  const pct = Math.round(strip.progress)

  return (
    <div
      style={{
        position: "sticky",
        top: 64,
        zIndex: 39,
        borderTop: "1px solid var(--border)",
        borderBottom: "1px solid var(--border)",
        background: "var(--surface)",
      }}
    >
      <div
        style={{
          maxWidth: 1480,
          margin: "0 auto",
          padding: "8px clamp(14px, 3vw, 28px)",
          display: "flex",
          alignItems: "center",
          gap: 12,
        }}
      >
        <Loader2 size={15} className="anim-spin" style={{ color: "var(--accent)", flexShrink: 0 }} />
        <span style={{ fontSize: 12.5, fontWeight: 500, whiteSpace: "nowrap" }}>{strip.label}</span>
        <div
          style={{
            flex: 1,
            height: 5,
            borderRadius: 4,
            background: "var(--surface2)",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              width: `${pct}%`,
              height: "100%",
              background: "var(--gradient)",
              transition: "width .3s ease",
            }}
          />
        </div>
        <span
          className="tabular"
          style={{ fontSize: 12, minWidth: 38, textAlign: "right", color: "var(--text2)" }}
        >
          {pct}%
        </span>
      </div>
    </div>
  )
}
