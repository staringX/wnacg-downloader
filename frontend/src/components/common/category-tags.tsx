interface CategoryTagsProps {
  tags: string[]
  style?: React.CSSProperties
}

// 详情页「分類」欄をスラッシュ分割したタグ群を chip 表示する
export function CategoryTags({ tags, style }: CategoryTagsProps) {
  if (tags.length === 0) return null
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 5, ...style }}>
      {tags.map((t) => (
        <span
          key={t}
          style={{
            fontSize: 10.5,
            fontWeight: 600,
            padding: "2px 7px",
            borderRadius: 6,
            background: "var(--accent-soft)",
            color: "var(--accent)",
            border: "1px solid color-mix(in srgb, var(--accent) 25%, transparent)",
            whiteSpace: "nowrap",
          }}
        >
          {t}
        </span>
      ))}
    </div>
  )
}
