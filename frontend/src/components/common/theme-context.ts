import { createContext, useContext } from "react"

export type Theme = "dark" | "light"

export interface ThemeContextValue {
  theme: Theme
  toggleTheme: () => void
}

export const ThemeContext = createContext<ThemeContextValue | null>(null)

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error("useTheme 必须在 ThemeProvider 内使用")
  return ctx
}
