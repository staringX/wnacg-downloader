import { useEffect, useState } from "react"
import { Trash2 } from "lucide-react"

interface Props {
  count: number
  onDelete: () => void
  onCancel: () => void
}

// DESIGN_SPEC §6.5 选择操作栏
export function SelectionBar({ count, onDelete, onCancel }: Props) {
  // 複数件の削除は取り消せないため 2 段階（1回目で確認、2回目で実行）
  const [confirm, setConfirm] = useState(false)
  useEffect(() => setConfirm(false), [count])

  const handleDelete = () => {
    if (!confirm) {
      setConfirm(true)
      return
    }
    onDelete()
  }

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
        {confirm ? (
          <>
            确认删除 <span className="tabular">{count}</span> 项？此操作无法撤销
          </>
        ) : (
          <>
            已选择 <span className="tabular">{count}</span> 项
          </>
        )}
      </span>
      <span style={{ flex: 1 }} />
      <button
        onClick={handleDelete}
        disabled={count === 0}
        onBlur={() => setConfirm(false)}
        className="touch-btn"
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 6,
          height: 34,
          padding: "0 14px",
          borderRadius: 9,
          border: `1px solid ${confirm ? "var(--danger-solid)" : "var(--danger)"}`,
          background: confirm ? "var(--danger-solid)" : "color-mix(in srgb, var(--danger) 14%, transparent)",
          color: confirm ? "#fff" : "var(--danger-strong)",
          fontSize: 13,
          fontWeight: 600,
          opacity: count === 0 ? 0.5 : 1,
        }}
      >
        <Trash2 size={15} />
        {confirm ? "确认删除" : "删除所选"}
      </button>
      <button
        onClick={onCancel}
        className="touch-btn"
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
