// 标签页组件
"use client"

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Library, Sparkles } from "lucide-react"
import { ReactNode } from "react"

interface AppTabsProps {
  collectionContent: ReactNode
  updatesContent: ReactNode
  onTabChange?: (value: string) => void
  value?: string
}

export function AppTabs({ collectionContent, updatesContent, onTabChange, value }: AppTabsProps) {
  return (
    <Tabs value={value} defaultValue="collection" className="w-full" onValueChange={onTabChange}>
      <TabsList className="mb-6 glass">
        <TabsTrigger value="collection" className="gap-2">
          <Library className="w-4 h-4" />
          我的收藏
        </TabsTrigger>
        <TabsTrigger value="updates" className="gap-2">
          <Sparkles className="w-4 h-4" />
          最近更新
        </TabsTrigger>
      </TabsList>

      <TabsContent value="collection">{collectionContent}</TabsContent>
      <TabsContent value="updates">{updatesContent}</TabsContent>
    </Tabs>
  )
}

