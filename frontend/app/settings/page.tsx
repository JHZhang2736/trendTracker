"use client"

import { useCallback, useEffect, useState } from "react"
import { Settings, RefreshCw, Trash2, CheckCircle, XCircle, Clock, Mail } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { api, type SystemConfig, type SchedulerStatus, type CollectorRunResponse } from "@/lib/api"
import { getPlatformMeta } from "@/lib/platform-config"

const PLATFORMS = ["weibo", "google", "tiktok"] as const

function StatusBadge({ ok, label }: { ok: boolean; label?: string }) {
  return ok ? (
    <Badge className="bg-green-500 hover:bg-green-500 gap-1">
      <CheckCircle className="w-3 h-3" />
      {label ?? "已配置"}
    </Badge>
  ) : (
    <Badge variant="secondary" className="gap-1 text-muted-foreground">
      <XCircle className="w-3 h-3" />
      {label ?? "未配置"}
    </Badge>
  )
}

export default function SettingsPage() {
  const [config, setConfig] = useState<SystemConfig | null>(null)
  const [scheduler, setScheduler] = useState<SchedulerStatus | null>(null)
  const [activePlatforms, setActivePlatforms] = useState<string[]>([])
  const [collecting, setCollecting] = useState(false)
  const [collectResult, setCollectResult] = useState<CollectorRunResponse | null>(null)
  const [clearing, setClearing] = useState(false)
  const [clearResult, setClearResult] = useState<{ deleted: number } | null>(null)
  const [loading, setLoading] = useState(true)
  const [clearDialogOpen, setClearDialogOpen] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [cfg, sched, topByPlatform] = await Promise.all([
        api.system.config(),
        api.scheduler.status(),
        api.trends.topByPlatform(1),
      ])
      setConfig(cfg)
      setScheduler(sched)
      setActivePlatforms(Object.keys(topByPlatform.platforms))
    } catch {
      // backend offline — leave nulls
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleCollect = async () => {
    setCollecting(true)
    setCollectResult(null)
    try {
      const result = await api.post<CollectorRunResponse>("/api/v1/collector/run", {})
      setCollectResult(result)
      await load()
    } finally {
      setCollecting(false)
    }
  }

  const handleClearAll = async () => {
    setClearing(true)
    setClearResult(null)
    try {
      const result = await api.trends.clearAll()
      setClearResult(result)
      await load()
    } finally {
      setClearing(false)
    }
  }

  const jobNameMap: Record<string, string> = {
    collect_trends: "采集热词",
    daily_brief: "生成日报",
    cleanup_old_trends: "清理旧数据",
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Settings className="w-6 h-6" />
          系统设置
        </h1>
        <p className="text-muted-foreground text-sm mt-1">配置状态与系统管理</p>
      </div>

      {/* 调度器 */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">调度器</CardTitle>
            {scheduler && (
              <Badge
                className={scheduler.running ? "bg-green-500 hover:bg-green-500" : ""}
                variant={scheduler.running ? "default" : "secondary"}
              >
                {scheduler.running ? "运行中" : "已停止"}
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {loading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => <Skeleton key={i} className="h-8 w-full" />)}
            </div>
          ) : scheduler ? (
            <>
              <div className="rounded-md border divide-y text-sm">
                {scheduler.jobs.map((job) => (
                  <div key={job.id} className="flex items-center justify-between px-3 py-2">
                    <span className="font-medium">{jobNameMap[job.id] ?? job.name}</span>
                    <div className="flex items-center gap-3 text-muted-foreground">
                      <span className="font-mono text-xs">{job.trigger}</span>
                      {job.next_run_time && (
                        <span className="flex items-center gap-1 text-xs">
                          <Clock className="w-3 h-3" />
                          {new Date(job.next_run_time).toLocaleString("zh-CN", {
                            month: "2-digit", day: "2-digit",
                            hour: "2-digit", minute: "2-digit",
                          })}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex items-center gap-3">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleCollect}
                  disabled={collecting}
                  className="gap-2"
                >
                  <RefreshCw className={`w-4 h-4 ${collecting ? "animate-spin" : ""}`} />
                  立即采集
                </Button>
                {collectResult && (
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-muted-foreground">采集完成，共 {collectResult.records_count} 条</span>
                    {collectResult.platforms.map((p) => (
                      <Badge
                        key={p.platform}
                        variant={p.error ? "destructive" : "secondary"}
                        className="text-xs"
                      >
                        {getPlatformMeta(p.platform).displayName}
                        {p.error ? " ✗" : ` +${p.count}`}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">无法获取调度器状态，后端可能未启动</p>
          )}
        </CardContent>
      </Card>

      {/* 数据源状态 */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">数据源状态</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex gap-2">
              {[1, 2, 3].map((i) => <Skeleton key={i} className="h-8 w-32 rounded-md" />)}
            </div>
          ) : (
            <div className="divide-y rounded-md border text-sm">
              {PLATFORMS.map((slug) => {
                const meta = getPlatformMeta(slug)
                const active = activePlatforms.includes(slug)
                const needsConfig = slug === "tiktok" && config && !config.tiktok.configured
                return (
                  <div key={slug} className="flex items-center justify-between px-3 py-2.5">
                    <div className="flex items-center gap-2">
                      <span
                        className="inline-block w-2 h-2 rounded-full"
                        style={{ backgroundColor: meta.color }}
                      />
                      <span className="font-medium">{meta.displayName}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {needsConfig && (
                        <span className="text-xs text-amber-500">需配置 TIKTOK_COOKIE</span>
                      )}
                      <Badge
                        variant={active ? "default" : "secondary"}
                        className={active ? "bg-green-500 hover:bg-green-500" : ""}
                      >
                        {active ? "近24h有数据" : "无近期数据"}
                      </Badge>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* AI 配置 */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">AI 配置</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <Skeleton className="h-16 w-full" />
          ) : config ? (
            <div className="divide-y rounded-md border text-sm">
              <div className="flex items-center justify-between px-3 py-2.5">
                <span className="text-muted-foreground">模型提供商</span>
                <span className="font-mono font-medium">{config.ai.provider}</span>
              </div>
              <div className="flex items-center justify-between px-3 py-2.5">
                <span className="text-muted-foreground">API Key</span>
                <StatusBadge ok={config.ai.configured} />
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">无法加载配置</p>
          )}
        </CardContent>
      </Card>

      {/* 邮件推送 */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Mail className="w-4 h-4" />
            邮件推送
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <Skeleton className="h-16 w-full" />
          ) : config ? (
            <div className="space-y-3">
              <div className="divide-y rounded-md border text-sm">
                <div className="flex items-center justify-between px-3 py-2.5">
                  <span className="text-muted-foreground">SMTP 配置</span>
                  <StatusBadge ok={config.email.configured} />
                </div>
                <div className="flex items-center justify-between px-3 py-2.5">
                  <span className="text-muted-foreground">SMTP 服务器</span>
                  <span className="font-mono text-xs">{config.email.smtp_host}</span>
                </div>
                <div className="flex items-center justify-between px-3 py-2.5">
                  <span className="text-muted-foreground">收件邮箱</span>
                  <span className="font-mono text-xs">
                    {config.email.recipient ?? "未设置"}
                  </span>
                </div>
              </div>
              {!config.email.configured && (
                <p className="text-xs text-muted-foreground">
                  在 .env 中配置 SMTP_USER、SMTP_PASSWORD、ALERT_EMAIL_TO 即可启用每日简报邮件推送
                </p>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">无法加载配置</p>
          )}
        </CardContent>
      </Card>

      {/* 数据管理 */}
      <Card className="border-destructive/40">
        <CardHeader className="pb-3">
          <CardTitle className="text-base text-destructive">数据管理</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            清空所有已采集的热词数据。此操作不可撤销，AI 简报不受影响。
          </p>
          <div className="flex items-center gap-4">
            <Button
              variant="destructive"
              size="sm"
              disabled={clearing}
              className="gap-2"
              onClick={() => setClearDialogOpen(true)}
            >
              <Trash2 className="w-4 h-4" />
              清空所有数据
            </Button>
            {clearResult && (
              <span className="text-sm text-muted-foreground">
                已删除 {clearResult.deleted} 条记录
              </span>
            )}
          </div>

          <AlertDialog open={clearDialogOpen} onOpenChange={setClearDialogOpen}>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>确认清空所有热词数据？</AlertDialogTitle>
                <AlertDialogDescription>
                  这将删除数据库中所有已采集的热词记录，操作不可撤销。AI 简报不会被删除。
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel onClick={() => setClearDialogOpen(false)}>
                  取消
                </AlertDialogCancel>
                <AlertDialogAction
                  className="bg-destructive hover:bg-destructive/90"
                  onClick={() => { setClearDialogOpen(false); handleClearAll() }}
                >
                  确认清空
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </CardContent>
      </Card>
    </div>
  )
}
