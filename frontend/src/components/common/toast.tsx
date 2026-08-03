import { useCallback, useRef, useState } from "react"
import type { ReactNode } from "react"
import { useIsMobile } from "@/hooks/use-mobile"
import { ToastContext } from "./toast-context"

// DESIGN_SPEC §6.13: 反转配色 / slideUp .25s / 2.2s 自动消失
export function ToastProvider({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState<string | null>(null)
  const [visibleKey, setVisibleKey] = useState(0)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const isMobile = useIsMobile()

  const toast = useCallback((msg: string) => {
    setMessage(msg)
    setVisibleKey((k) => k + 1)
    if (timerRef.current) clearTimeout(timerRef.current)
    // 3s：2.2s は長めのメッセージだと読み切れないことがあるため（推奨 3〜5s）
    timerRef.current = setTimeout(() => setMessage(null), 3000)
  }, [])

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      {message && (
        <div
          key={visibleKey}
          // 操作結果はスクリーンリーダーにも伝える（フォーカスは奪わない）
          role="status"
          aria-live="polite"
          style={{
            position: "fixed",
            left: "50%",
            transform: "translateX(-50%)",
            // iOS のホームインジケータ分を足して隠れないようにする
            bottom: `calc(${isMobile ? 92 : 28}px + env(safe-area-inset-bottom, 0px))`,
            zIndex: 70,
            padding: "11px 20px",
            borderRadius: 12,
            background: "var(--text)",
            color: "var(--bg)",
            fontSize: 13,
            fontWeight: 500,
            boxShadow: "0 12px 30px rgba(0,0,0,.4)",
            maxWidth: "calc(100vw - 32px)",
            textAlign: "center",
            animation: "slideUp .25s ease",
          }}
        >
          {message}
        </div>
      )}
    </ToastContext.Provider>
  )
}
