import { useEffect, useState } from "react"

// DESIGN_SPEC §7: window.innerWidth < 820 判定为移动端
const MOBILE_BREAKPOINT = 820

export function useIsMobile() {
  const [isMobile, setIsMobile] = useState<boolean>(
    typeof window !== "undefined" ? window.innerWidth < MOBILE_BREAKPOINT : false
  )

  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth < MOBILE_BREAKPOINT)
    window.addEventListener("resize", onResize)
    onResize()
    return () => window.removeEventListener("resize", onResize)
  }, [])

  return isMobile
}
