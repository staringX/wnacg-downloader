"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { RefreshCw } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { api } from "@/lib/api"

interface SyncButtonProps {
  onSyncComplete?: () => void
}

export function SyncButton({ onSyncComplete }: SyncButtonProps) {
  const [isSyncing, setIsSyncing] = useState(false)
  const { toast } = useToast()

  const handleSync = async () => {
    setIsSyncing(true)
    try {
      const response = await api.syncCollection()

      if (response.success) {
        toast({
          title: "同步成功",
          description: `已同步收藏夹数据`,
        })
        onSyncComplete?.()
      } else {
        throw new Error(response.error || "同步失败")
      }
    } catch (error) {
      console.error("[v0] Sync error:", error)
      toast({
        title: "同步失败",
        description: error instanceof Error ? error.message : "请稍后重试",
        variant: "destructive",
      })
    } finally {
      setIsSyncing(false)
    }
  }

  return (
    <Button
      onClick={handleSync}
      disabled={isSyncing}
      variant="outline"
      className="glass-card hover:shadow-lg transition-all bg-transparent"
    >
      <RefreshCw className={`w-4 h-4 mr-2 ${isSyncing ? "animate-spin" : ""}`} />
      {isSyncing ? "同步中..." : "同步收藏夹"}
    </Button>
  )
}
