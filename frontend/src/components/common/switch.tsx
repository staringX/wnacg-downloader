// DESIGN_SPEC §6.11: 44×26 ピル开关，ON=accent / OFF=--border
interface SwitchProps {
  checked: boolean
  onChange: (checked: boolean) => void
  id?: string
  // スクリーンリーダー用の名前（視覚ラベルは隣のテキストで button 自体は無名のため）
  label?: string
}

export function Switch({ checked, onChange, id, label }: SwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      id={id}
      onClick={() => onChange(!checked)}
      style={{
        // 見た目は 44×26 のまま、タップ領域だけ 44×44 に広げる。
        // 上下 9px の余白は負マージンで打ち消すのでレイアウトは変わらない。
        width: 44,
        height: 44,
        margin: "-9px 0",
        padding: 0,
        border: "none",
        background: "transparent",
        flexShrink: 0,
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        borderRadius: 14,
      }}
    >
      <span
        aria-hidden="true"
        style={{
          position: "relative",
          display: "block",
          width: 44,
          height: 26,
          borderRadius: 14,
          background: checked ? "var(--accent)" : "var(--border)",
          transition: "background .2s",
        }}
      >
        <span
          style={{
            position: "absolute",
            top: 3,
            left: checked ? 21 : 3,
            width: 20,
            height: 20,
            borderRadius: "50%",
            background: "#fff",
            boxShadow: "0 1px 3px rgba(0,0,0,.3)",
            transition: "left .2s",
          }}
        />
      </span>
    </button>
  )
}
