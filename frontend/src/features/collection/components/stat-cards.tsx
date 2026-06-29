import { Library, CheckCircle2, Download } from "lucide-react"

interface StatCardsProps {
  total: number
  downloaded: number
  pending: number
}

interface CardDef {
  label: string
  value: number
  color: string
  Icon: typeof Library
}

// DESIGN_SPEC §6.3 统计卡片
export function StatCards({ total, downloaded, pending }: StatCardsProps) {
  const cards: CardDef[] = [
    { label: "总计", value: total, color: "var(--text)", Icon: Library },
    { label: "已下载", value: downloaded, color: "var(--state-downloaded)", Icon: CheckCircle2 },
    { label: "待下载", value: pending, color: "var(--accent)", Icon: Download },
  ]

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
        gap: 12,
      }}
    >
      {cards.map((c) => (
        <div
          key={c.label}
          style={{
            position: "relative",
            overflow: "hidden",
            padding: "16px 18px",
            borderRadius: 16,
            background: "var(--surface)",
            border: "1px solid var(--border)",
          }}
        >
          <div
            style={{
              fontSize: 11.5,
              fontWeight: 500,
              letterSpacing: "0.03em",
              color: "var(--text2)",
            }}
          >
            {c.label}
          </div>
          <div
            className="font-display tabular"
            style={{ fontSize: 30, fontWeight: 700, lineHeight: 1.1, color: c.color, marginTop: 4 }}
          >
            {c.value}
          </div>
          <c.Icon
            size={60}
            style={{
              position: "absolute",
              right: 12,
              bottom: 8,
              color: c.color,
              opacity: 0.13,
              pointerEvents: "none",
            }}
          />
        </div>
      ))}
    </div>
  )
}
