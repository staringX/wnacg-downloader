// DESIGN_SPEC §6.11: 44×26 ピル开关，ON=accent / OFF=--border
interface SwitchProps {
  checked: boolean
  onChange: (checked: boolean) => void
  id?: string
}

export function Switch({ checked, onChange, id }: SwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      id={id}
      onClick={() => onChange(!checked)}
      style={{
        position: "relative",
        width: 44,
        height: 26,
        borderRadius: 14,
        border: "none",
        flexShrink: 0,
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
    </button>
  )
}
