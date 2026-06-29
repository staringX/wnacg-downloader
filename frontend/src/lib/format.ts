// 显示用工具函数

// 封面占位渐变索引（按 index % 6 循环），DESIGN_SPEC §1.4
export function coverGradClass(index: number): string {
  return `cover-grad-${((index % 6) + 6) % 6}`
}

// 根据字符串稳定地派生一个渐变索引（无图时使用）
export function coverIndexFromKey(key: string): number {
  let h = 0
  for (let i = 0; i < key.length; i++) {
    h = (h * 31 + key.charCodeAt(i)) | 0
  }
  return Math.abs(h)
}

// 更新日时显示（DESIGN_SPEC §4.4），返回 YYYY-MM-DD
export function formatDate(value: string | null | undefined): string {
  if (!value) return ""
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return ""
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, "0")
  const day = String(d.getDate()).padStart(2, "0")
  return `${y}-${m}-${day}`
}
