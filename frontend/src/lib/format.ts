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

// 「最后更新」表示用：YYYY-MM-DD HH:mm（値が無ければ空文字）
export function formatDateTime(value: string | null | undefined): string {
  const date = formatDate(value)
  if (!date) return ""
  const d = new Date(value as string)
  const hh = String(d.getHours()).padStart(2, "0")
  const mm = String(d.getMinutes()).padStart(2, "0")
  return `${date} ${hh}:${mm}`
}

// 详情页「分類」欄をスラッシュ（全角／半角）で分割してタグ配列にする
export function categoryTags(value: string | null | undefined): string[] {
  if (!value) return []
  return value
    .split(/[／/]/)
    .map((s) => s.trim())
    .filter(Boolean)
}
