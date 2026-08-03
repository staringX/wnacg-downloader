import { RefreshCw } from "lucide-react"

interface SyncFabProps {
  onSync: () => void
  syncing: boolean
  // 更新中・ダウンロード中は起動できない（押しても 409 になるため）
  disabled?: boolean
  label: string
}

// DESIGN_SPEC §6.12 移动端同步 FAB
export function SyncFab({ onSync, syncing, disabled = false, label }: SyncFabProps) {
  return (
    <button
      onClick={onSync}
      disabled={disabled}
      aria-label={label}
      title={disabled ? "下载或更新进行中，暂不可执行" : label}
      style={{
        position: "fixed",
        right: 18,
        // ホームインジケータに重ならないよう下端に安全余白を足す
        bottom: "calc(24px + env(safe-area-inset-bottom, 0px))",
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
        opacity: disabled ? 0.5 : 1,
        cursor: disabled ? "not-allowed" : "pointer",
        boxShadow: "0 10px 28px color-mix(in srgb, var(--accent) 50%, transparent)",
      }}
    >
      <RefreshCw size={24} className={syncing ? "anim-spin" : undefined} />
    </button>
  )
}
