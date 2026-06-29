import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import "./index.css"
import { ThemeProvider } from "@/components/common/theme-provider"
import { ToastProvider } from "@/components/common/toast"
import { App } from "@/App"

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <ToastProvider>
        <App />
      </ToastProvider>
    </ThemeProvider>
  </StrictMode>
)
