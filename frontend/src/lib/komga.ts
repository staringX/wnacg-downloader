// Komga 本地阅读跳转（沿用旧 header 逻辑：同主机 25601 端口）
export function openKomga() {
  const komgaUrl = `${window.location.protocol}//${window.location.hostname}:25601`
  window.open(komgaUrl, "_blank")
}

// 原站点打开（在线阅读）
export function openOriginalSite(url: string | null | undefined) {
  if (url) window.open(url, "_blank")
}
