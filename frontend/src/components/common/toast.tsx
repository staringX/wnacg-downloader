import { createContext, useContext, useCallback, useRef, useState } from "react"
import type { ReactNode } from "react"
import { useIsMobile } from "@/hooks/use-mobile"

interface ToastContextValue {
  toast: (message: string) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

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
    timerRef.current = setTimeout(() => setMessage(null), 2200)
  }, [])

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      {message && (
        <div
          key={visibleKey}
          style={{
            position: "fixed",
            left: "50%",
            transform: "translateX(-50%)",
            bottom: isMobile ? 92 : 28,
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

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error("useToast 必须在 ToastProvider 内使用")
  return ctx
}
