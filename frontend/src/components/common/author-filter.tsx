import { useMemo, useState } from "react"
import { Users, Search, Check, X } from "lucide-react"

interface AuthorFilterProps {
  authors: string[]
  selected: Set<string>
  onChange: (next: Set<string>) => void
  // モバイルの 1 行レイアウト用：親の flex 行で幅を分け合う細身のボタンにする
  compact?: boolean
}

// 作者マルチ選択フィルタ（作者検索付きのポップオーバー）
// 収藏夹・最近更新の両画面で共用する。
export function AuthorFilter({ authors, selected, onChange, compact = false }: AuthorFilterProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState("")

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return authors
    return authors.filter((a) => a.toLowerCase().includes(q))
  }, [authors, query])

  const toggle = (a: string) => {
    const next = new Set(selected)
    if (next.has(a)) next.delete(a)
    else next.add(a)
    onChange(next)
  }

  const active = selected.size > 0

  return (
    <div style={{ position: "relative", ...(compact ? { flex: "1 1 auto", minWidth: 0 } : null) }}>
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          display: compact ? "flex" : "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          gap: compact ? 5 : 7,
          width: compact ? "100%" : undefined,
          height: compact ? 36 : 40,
          padding: compact ? "0 8px" : "0 14px",
          borderRadius: compact ? 10 : 11,
          fontSize: compact ? 12.5 : 13.5,
          fontWeight: 500,
          whiteSpace: "nowrap",
          overflow: "hidden",
          border: `1px solid ${active ? "var(--accent)" : "var(--border)"}`,
          background: active ? "var(--accent-soft)" : "var(--surface)",
          color: active ? "var(--accent)" : "var(--text)",
        }}
      >
        <Users size={compact ? 15 : 16} style={{ flexShrink: 0 }} />
        <span style={{ overflow: "hidden", textOverflow: "ellipsis", minWidth: 0 }}>作者筛选</span>
        {active && (
          <span
            className="tabular"
            style={{
              flexShrink: 0,
              fontSize: 11,
              fontWeight: 700,
              padding: "1px 6px",
              borderRadius: 20,
              background: "var(--accent)",
              color: "#fff",
            }}
          >
            {selected.size}
          </span>
        )}
      </button>

      {open && (
        <>
          <div
            style={{ position: "fixed", inset: 0, zIndex: 45 }}
            onClick={() => setOpen(false)}
          />
          <div
            className="anim-popin"
            style={{
              position: "absolute",
              top: compact ? 42 : 46,
              left: 0,
              zIndex: 46,
              width: 260,
              maxWidth: "90vw",
              borderRadius: 13,
              background: "var(--surface)",
              border: "1px solid var(--border)",
              boxShadow: "0 20px 50px rgba(0,0,0,.4)",
              padding: 8,
              display: "flex",
              flexDirection: "column",
              gap: 8,
            }}
          >
            {/* 作者搜索 */}
            <div style={{ position: "relative" }}>
              <Search
                size={15}
                style={{
                  position: "absolute",
                  left: 11,
                  top: "50%",
                  transform: "translateY(-50%)",
                  color: "var(--text2)",
                  pointerEvents: "none",
                }}
              />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="搜索作者…"
                autoFocus
                style={{
                  width: "100%",
                  height: 36,
                  padding: "0 30px 0 33px",
                  borderRadius: 9,
                  border: "1px solid var(--border)",
                  background: "var(--surface2)",
                  color: "var(--text)",
                  fontSize: 13,
                  outline: "none",
                }}
              />
              {active && (
                <button
                  onClick={() => onChange(new Set())}
                  aria-label="清除筛选"
                  style={{
                    position: "absolute",
                    right: 6,
                    top: "50%",
                    transform: "translateY(-50%)",
                    width: 22,
                    height: 22,
                    borderRadius: 6,
                    border: "none",
                    background: "var(--surface)",
                    color: "var(--text2)",
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <X size={14} />
                </button>
              )}
            </div>

            {/* 作者列表 */}
            <div style={{ maxHeight: 280, overflowY: "auto", display: "flex", flexDirection: "column", gap: 2 }}>
              {filtered.length === 0 ? (
                <div style={{ padding: "16px 8px", textAlign: "center", fontSize: 12.5, color: "var(--text2)" }}>
                  没有匹配的作者
                </div>
              ) : (
                filtered.map((a) => {
                  const checked = selected.has(a)
                  return (
                    <button
                      key={a}
                      onClick={() => toggle(a)}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 9,
                        width: "100%",
                        padding: "8px 9px",
                        borderRadius: 8,
                        border: "none",
                        background: checked ? "var(--accent-soft)" : "transparent",
                        color: "var(--text)",
                        fontSize: 13,
                        textAlign: "left",
                        cursor: "pointer",
                      }}
                    >
                      <span
                        style={{
                          width: 17,
                          height: 17,
                          borderRadius: 5,
                          flexShrink: 0,
                          border: `1.5px solid ${checked ? "var(--accent)" : "var(--border)"}`,
                          background: checked ? "var(--accent)" : "transparent",
                          display: "inline-flex",
                          alignItems: "center",
                          justifyContent: "center",
                          color: "#fff",
                        }}
                      >
                        {checked && <Check size={12} strokeWidth={3} />}
                      </span>
                      <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {a}
                      </span>
                    </button>
                  )
                })
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
