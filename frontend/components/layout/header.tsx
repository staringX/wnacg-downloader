// 页面头部组件
"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Download, ImageIcon, CheckCircle2, X, Users, RefreshCw } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { syncApi } from "@/lib/api"
import { useTaskStatus, useRunningTasks } from "@/hooks/use-task-status"
import { MobileMenu } from "./mobile-menu"

interface HeaderProps {
  totalMangas: number
  downloadedMangas: number
  pendingMangas: number
  showPreview: boolean
  onPreviewChange: (show: boolean) => void
  selectionMode: boolean
  onToggleSelectionMode: () => void
  selectedCount: number
  onBatchDelete: () => void
  onDownloadAllPending: () => void
  onSyncComplete: () => void
  // 新增props
  currentTab: "collection" | "updates"
  groupByAuthor: boolean
  onGroupByAuthorChange: (value: boolean) => void
  onSyncRecentUpdates: () => void
  onDownloadAllUpdates: () => void
  pendingUpdatesCount: number
}

export function Header({
  totalMangas,
  downloadedMangas,
  pendingMangas,
  showPreview,
  onPreviewChange,
  selectionMode,
  onToggleSelectionMode,
  selectedCount,
  onBatchDelete,
  onDownloadAllPending,
  onSyncComplete,
  currentTab,
  groupByAuthor,
  onGroupByAuthorChange,
  onSyncRecentUpdates,
  onDownloadAllUpdates,
  pendingUpdatesCount,
}: HeaderProps) {
  const [isScrolled, setIsScrolled] = useState(false)
  const [lastScrollY, setLastScrollY] = useState(0)
  const [isVisible, setIsVisible] = useState(true)
  const [isMobile, setIsMobile] = useState(false)
  const { toast } = useToast()

  // 同步收藏夹相关状态
  const [collectionTaskId, setCollectionTaskId] = useState<string | null>(null)
  const { task: collectionTask, isLoading: isCollectionTaskLoading } = useTaskStatus(collectionTaskId)
  const { tasks: collectionRunningTasks } = useRunningTasks("sync")

  // 同步最近更新相关状态
  const [updatesTaskId, setUpdatesTaskId] = useState<string | null>(null)
  const { task: updatesTask, isLoading: isUpdatesTaskLoading } = useTaskStatus(updatesTaskId)
  const { tasks: updatesRunningTasks } = useRunningTasks("sync_recent_updates")

  // 检查是否有正在运行的同步收藏夹任务
  useEffect(() => {
    if (collectionRunningTasks.length > 0 && !collectionTaskId) {
      setCollectionTaskId(collectionRunningTasks[0].id)
    }
  }, [collectionRunningTasks, collectionTaskId])

  // 检查是否有正在运行的同步最近更新任务
  useEffect(() => {
    if (updatesRunningTasks.length > 0 && !updatesTaskId) {
      setUpdatesTaskId(updatesRunningTasks[0].id)
    }
  }, [updatesRunningTasks, updatesTaskId])

  // 监听收藏夹同步任务状态变化
  useEffect(() => {
    if (!collectionTask) return

    if (collectionTask.status === "completed") {
      toast({
        title: "同步完成",
        description: collectionTask.message || "已同步收藏夹数据",
      })
      onSyncComplete()
      setCollectionTaskId(null)
    } else if (collectionTask.status === "failed") {
      toast({
        title: "同步失败",
        description: collectionTask.error_message || "同步过程中出现错误",
        variant: "destructive",
      })
      setCollectionTaskId(null)
    }
  }, [collectionTask, toast, onSyncComplete])

  // 监听最近更新同步任务状态变化
  useEffect(() => {
    if (!updatesTask) return

    if (updatesTask.status === "completed") {
      toast({
        title: "同步完成",
        description: updatesTask.message || "已同步最近更新",
      })
      onSyncRecentUpdates()
      setUpdatesTaskId(null)
    } else if (updatesTask.status === "failed") {
      toast({
        title: "同步失败",
        description: updatesTask.error_message || "同步过程中出现错误",
        variant: "destructive",
      })
      setUpdatesTaskId(null)
    }
  }, [updatesTask, toast, onSyncRecentUpdates])

  // 根据当前tab获取同步状态
  const isSyncing = currentTab === "collection"
    ? collectionTask?.status === "running" || collectionTask?.status === "pending" || isCollectionTaskLoading
    : updatesTask?.status === "running" || updatesTask?.status === "pending" || isUpdatesTaskLoading

  const hasRunningTask = currentTab === "collection"
    ? collectionRunningTasks.length > 0
    : updatesRunningTasks.length > 0

  const currentTask = currentTab === "collection" ? collectionTask : updatesTask
  const progressText = currentTask?.progress
    ? ` (${currentTask.progress}%)`
    : currentTask?.message
    ? ` - ${currentTask.message}`
    : ""

  // 统一的同步处理函数
  const handleSync = async () => {
    if (hasRunningTask) {
      toast({
        title: "同步进行中",
        description: "已有同步任务正在运行，请等待完成",
        variant: "default",
      })
      return
    }

    try {
      if (currentTab === "collection") {
        const response = await syncApi.syncCollection()
        if (response.success && response.data) {
          setCollectionTaskId(response.data.task_id)
          toast({
            title: "同步已开始",
            description: "同步任务已创建，正在后台执行...",
          })
        } else {
          throw new Error(response.error || "同步失败")
        }
      } else {
        const response = await syncApi.syncRecentUpdates()
        if (response.success && response.data) {
          setUpdatesTaskId(response.data.task_id)
          toast({
            title: "同步已开始",
            description: "同步任务已创建，正在后台执行...",
          })
        } else {
          throw new Error(response.error || "同步失败")
        }
      }
    } catch (error) {
      console.error("Sync error:", error)
      toast({
        title: "同步失败",
        description: error instanceof Error ? error.message : "请稍后重试",
        variant: "destructive",
      })
    }
  }

  // 根据当前tab获取待下载数量
  const pendingCount = currentTab === "collection" ? pendingMangas : pendingUpdatesCount

  // 根据当前tab获取下载全部函数
  const handleDownloadAll = currentTab === "collection" ? onDownloadAllPending : onDownloadAllUpdates

  // 检测是否为移动端
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 1024) // lg breakpoint
    }
    
    checkMobile()
    window.addEventListener("resize", checkMobile)
    return () => window.removeEventListener("resize", checkMobile)
  }, [])

  // 监听滚动，实现自动隐藏/显示（仅移动端）
  useEffect(() => {
    if (!isMobile) {
      setIsVisible(true)
      return
    }

    const handleScroll = () => {
      const currentScrollY = window.scrollY
      
      // 在顶部时始终显示
      if (currentScrollY < 10) {
        setIsScrolled(false)
        setIsVisible(true)
        setLastScrollY(currentScrollY)
        return
      }

      setIsScrolled(true)
      
      // 向下滚动时隐藏，向上滚动时显示
      if (currentScrollY > lastScrollY && currentScrollY > 100) {
        setIsVisible(false)
      } else if (currentScrollY < lastScrollY) {
        setIsVisible(true)
      }
      
      setLastScrollY(currentScrollY)
    }

    window.addEventListener("scroll", handleScroll, { passive: true })
    return () => window.removeEventListener("scroll", handleScroll)
  }, [lastScrollY, isMobile])

  return (
    <>
      <header
        className={`glass-header sticky z-10 transition-transform duration-300 ${
          isVisible ? "translate-y-0" : "-translate-y-full"
        } ${isScrolled ? "shadow-lg" : ""}`}
        style={{ top: 0 }}
      >
        <div className="container mx-auto px-4 py-4">
          {/* 桌面端布局 - 完全保持原样 */}
          <div className="hidden lg:flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-balance bg-gradient-to-r from-primary via-primary/80 to-primary/60 bg-clip-text text-transparent">
                漫画下载管理器
              </h1>
              <p className="text-sm text-muted-foreground mt-1">
                总计: {totalMangas} | 已下载: {downloadedMangas} | 待下载: {pendingMangas}
              </p>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 glass-card px-3 py-2 rounded-lg">
                <ImageIcon className="w-4 h-4 text-muted-foreground" />
                <Label htmlFor="preview-toggle" className="text-sm cursor-pointer">
                  预览图
                </Label>
                <Switch id="preview-toggle" checked={showPreview} onCheckedChange={onPreviewChange} />
              </div>

              {/* 按作者分类切换按钮 */}
              <div className="flex items-center gap-2 glass-card px-3 py-2 rounded-lg">
                <Users className="w-4 h-4 text-muted-foreground" />
                <Label htmlFor="group-by-author-toggle" className="text-sm cursor-pointer">
                  按作者分类
                </Label>
                <Switch
                  id="group-by-author-toggle"
                  checked={groupByAuthor}
                  onCheckedChange={onGroupByAuthorChange}
                />
              </div>

              <Button
                onClick={onToggleSelectionMode}
                variant={selectionMode ? "default" : "outline"}
                className={
                  selectionMode
                    ? "bg-primary text-primary-foreground"
                    : "glass-card bg-transparent hover:bg-primary/10"
                }
              >
                <CheckCircle2 className="w-4 h-4 mr-2" />
                {selectionMode ? "退出多选" : "多选模式"}
              </Button>

              {selectionMode && selectedCount > 0 && (
                <Button
                  onClick={onBatchDelete}
                  className="bg-red-500 text-white hover:bg-red-600 hover:scale-105 active:scale-95 transition-all duration-200 shadow-lg"
                >
                  <X className="w-4 h-4 mr-2" />
                  删除选中 ({selectedCount})
                </Button>
              )}

              {/* 统一的同步按钮 */}
              <Button
                onClick={handleSync}
                disabled={isSyncing || hasRunningTask}
                variant="outline"
                className="glass-card hover:shadow-lg transition-all bg-transparent"
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${isSyncing ? "animate-spin" : ""}`} />
                {isSyncing
                  ? `同步中...${progressText}`
                  : currentTab === "collection"
                  ? "同步收藏夹"
                  : "同步最近更新"}
              </Button>

              {/* 统一的全部下载按钮 */}
              {!selectionMode && pendingCount > 0 && (
                <Button
                  onClick={handleDownloadAll}
                  className="bg-primary text-primary-foreground hover:bg-primary/90 hover:scale-105 active:scale-95 transition-all duration-200 shadow-lg"
                >
                  <Download className="w-4 h-4 mr-2" />
                  {currentTab === "collection"
                    ? `下载全部待下载 (${pendingCount})`
                    : `下载全部新更新 (${pendingCount})`}
                </Button>
              )}
            </div>
          </div>

          {/* 移动端布局 - 只显示标题和统计信息 */}
          <div className="lg:hidden">
            <div>
              <h1 className="text-xl font-bold text-balance bg-gradient-to-r from-primary via-primary/80 to-primary/60 bg-clip-text text-transparent">
                漫画下载管理器
              </h1>
              <p className="text-xs text-muted-foreground mt-1">
                总计: {totalMangas} | 已下载: {downloadedMangas} | 待下载: {pendingMangas}
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* 移动端菜单按钮 - 悬浮在右上角 */}
      <div className="lg:hidden">
        <MobileMenu
          showPreview={showPreview}
          onPreviewChange={onPreviewChange}
          selectionMode={selectionMode}
          onToggleSelectionMode={onToggleSelectionMode}
          selectedCount={selectedCount}
          onBatchDelete={onBatchDelete}
          pendingCount={pendingCount}
          onDownloadAll={handleDownloadAll}
          onSync={handleSync}
          isSyncing={isSyncing}
          syncProgressText={progressText}
          currentTab={currentTab}
          groupByAuthor={groupByAuthor}
          onGroupByAuthorChange={onGroupByAuthorChange}
        />
      </div>
    </>
  )
}

