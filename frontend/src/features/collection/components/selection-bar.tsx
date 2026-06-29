import { Trash2 } from "lucide-react"

interface Props {
  count: number
  onDelete: () => void
  onCancel: () => void
}

// DESIGN_SPEC §6.5 选择操作栏
export function SelectionBar({ count, onDelete, onCancel }: Props) {
  return (
    <div
      className="anim-slideup"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "11px 15px",
        borderRadius: 13,
        background: "color-mix(in srgb, var(--accent) 10%, var(--surface))",
        border: "1px solid color-mix(in srgb, var(--accent) 35%, var(--border))",
      }}
    >
      <span style={{ fontSize: 13.5, fontWeight: 500 }}>
        已选择 <span className="tabular">{count}</span> 项
      </span>
      <span style={{ flex: 1 }} />
      <button
        onClick={onDelete}
        disabled={count === 0}
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 6,
          height: 34,
          padding: "0 14px",
          borderRadius: 9,
          border: "1px solid var(--danger)",
          background: "color-mix(in srgb, var(--danger) 14%, transparent)",
          color: "var(--danger)",
          fontSize: 13,
          fontWeight: 600,
          opacity: count === 0 ? 0.5 : 1,
        }}
      >
        <Trash2 size={15} />
        删除所选
      </button>
      <button
        onClick={onCancel}
        style={{
          height: 34,
          padding: "0 14px",
          borderRadius: 9,
          border: "1px solid var(--border)",
          background: "var(--surface)",
          color: "var(--text)",
          fontSize: 13,
        }}
      >
        取消
      </button>
    </div>
  )
}
