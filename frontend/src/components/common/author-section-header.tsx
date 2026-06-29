import { ChevronDown } from "lucide-react"

interface Props {
  author: string
  count: number
  collapsed: boolean
  onToggle: () => void
}

// DESIGN_SPEC §6.6 作者分组折叠标题
export function AuthorSectionHeader({ author, count, collapsed, onToggle }: Props) {
  return (
    <button
      onClick={onToggle}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        width: "100%",
        background: "transparent",
        border: "none",
        borderBottom: "1px solid var(--border)",
        paddingBottom: 8,
        marginBottom: 13,
        textAlign: "left",
        color: "var(--text)",
      }}
    >
      <ChevronDown
        size={15}
        style={{
          color: "var(--text2)",
          transform: collapsed ? "rotate(-90deg)" : "none",
          transition: "transform .2s",
        }}
      />
      <span style={{ fontSize: 15, fontWeight: 700 }}>{author}</span>
      <span className="tabular" style={{ fontSize: 12, color: "var(--text2)" }}>
        {count} 部
      </span>
      <span style={{ flex: 1 }} />
      <span style={{ fontSize: 12, color: "var(--text2)" }}>{collapsed ? "展开" : "收起"}</span>
    </button>
  )
}
