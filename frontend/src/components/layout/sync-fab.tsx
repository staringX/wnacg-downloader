import { RefreshCw } from "lucide-react"

// DESIGN_SPEC §6.12 移动端同步 FAB
export function SyncFab({ onSync, syncing }: { onSync: () => void; syncing: boolean }) {
  return (
    <button
      onClick={onSync}
      aria-label="同步收藏夹"
      style={{
        position: "fixed",
        right: 18,
        bottom: 24,
        zIndex: 45,
        width: 56,
        height: 56,
        borderRadius: 18,
        border: "none",
        background: "var(--gradient)",
        color: "#fff",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        boxShadow: "0 10px 28px color-mix(in srgb, var(--accent) 50%, transparent)",
      }}
    >
      <RefreshCw size={24} className={syncing ? "anim-spin" : undefined} />
    </button>
  )
}
