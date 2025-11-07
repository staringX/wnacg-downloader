import type React from "react"
import type { Metadata } from "next"

import { Toaster } from "@/components/toaster"
import "./globals.css"

export const metadata: Metadata = {
  title: "漫画下载管理器",
  description: "管理和下载你的漫画收藏",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="zh-CN">
      <body className={`font-sans antialiased`}>
        {children}
        <Toaster />
      </body>
    </html>
  )
}
