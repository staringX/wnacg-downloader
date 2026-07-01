import { createContext, useContext } from "react"

export interface ToastContextValue {
  toast: (message: string) => void
}

export const ToastContext = createContext<ToastContextValue | null>(null)

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error("useToast 必须在 ToastProvider 内使用")
  return ctx
}
