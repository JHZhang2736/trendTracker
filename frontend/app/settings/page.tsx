"use client"

import { useCallback, useEffect, useState } from "react"
import { Settings, Trash2, CheckCircle, XCircle, Clock, Mail, Newspaper, Briefcase, Radio } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
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
import { api, type SystemConfig, type SchedulerStatus } from "@/lib/api"
import { getPlatformMeta } from "@/lib/platform-config"

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
  const [platformLastPull, setPlatformLastPull] = useState<Record<string, string>>({})
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
      const lastPull: Record<string, string> = {}
      for (const [platform, items] of Object.entries(topByPlatform.platforms)) {
        if (items.length > 0) {
          lastPull[platform] = items[0].collected_at
        }
      }
      setPlatformLastPull(lastPull)
    } catch {
      // backend offline — leave nulls
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleToggleBusiness = async () => {
    if (!config) return
    const newShow = !config.deep_analysis.show_business
    try {
      await api.system.setShowBusiness(newShow)
      setConfig({ ...config, deep_analysis: { show_business: newShow } })
    } catch {
      /* ignore */
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

  const handleTogglePlatform = async (platform: string, enabled: boolean) => {
    if (!config) return
    try {
      await api.system.togglePlatform(platform, enabled)
      setConfig({
        ...config,
        platforms: { ...config.platforms, [platform]: enabled },
      })
    } catch {
      /* ignore */
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
            </>
          ) : (
            <p className="text-sm text-muted-foreground">无法获取调度器状态，后端可能未启动</p>
          )}
        </CardContent>
      </Card>

      {/* 信息源开关 */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Radio className="w-4 h-4" />
            信息源管理
          </CardTitle>
          <p className="text-xs text-muted-foreground">
            关闭的信息源不会参与采集，仪表盘和趋势列表中也不会显示对应数据
          </p>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => <Skeleton key={i} className="h-10 w-full" />)}
            </div>
          ) : config ? (
            <div className="space-y-3">
              {(() => {
                const slugs = Object.keys(config.platforms ?? {})
                const grouped: Record<string, string[]> = {}
                for (const slug of slugs) {
                  const cat = getPlatformMeta(slug).category
                  if (!grouped[cat]) grouped[cat] = []
                  grouped[cat].push(slug)
                }
                return Object.entries(grouped).map(([category, platforms]) => (
                  <div key={category}>
                    <p className="text-xs text-muted-foreground mb-1.5 font-medium">{category}</p>
                    <div className="divide-y rounded-md border text-sm">
                      {platforms.map((slug) => {
                        const meta = getPlatformMeta(slug)
                        const enabled = config.platforms?.[slug] ?? true
                        return (
                          <div key={slug} className="flex items-center justify-between px-3 py-2">
                            <div className="flex items-center gap-2">
                              <span
                                className="inline-block w-2 h-2 rounded-full"
                                style={{ backgroundColor: enabled ? meta.color : "#d1d5db" }}
                              />
                              <span className={`font-medium ${!enabled ? "text-muted-foreground" : ""}`}>
                                {meta.displayName}
                              </span>
                            </div>
                            <Switch
                              checked={enabled}
                              onCheckedChange={(checked) => handleTogglePlatform(slug, checked)}
                            />
                          </div>
                        )
                      })}
                    </div>
                  </div>
                ))
              })()}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">无法加载配置</p>
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
              {Object.keys(config?.platforms ?? {}).map((slug) => {
                const meta = getPlatformMeta(slug)
                const enabled = config?.platforms?.[slug] ?? true
                if (!enabled) return null
                const lastPull = platformLastPull[slug]
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
                      {lastPull ? (
                        <span className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Clock className="w-3 h-3" />
                          {new Date(lastPull).toLocaleString("zh-CN", {
                            month: "2-digit", day: "2-digit",
                            hour: "2-digit", minute: "2-digit",
                          })}
                        </span>
                      ) : (
                        <Badge variant="secondary" className="text-muted-foreground">
                          无近期数据
                        </Badge>
                      )}
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
              <div className="flex items-center justify-between px-3 py-2.5">
                <span className="text-muted-foreground">显示商业分析</span>
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1.5 h-7 text-xs"
                  onClick={handleToggleBusiness}
                >
                  {config.deep_analysis.show_business ? (
                    <>
                      <Briefcase className="w-3.5 h-3.5" />
                      已开启
                    </>
                  ) : (
                    <>
                      <Newspaper className="w-3.5 h-3.5" />
                      已关闭
                    </>
                  )}
                </Button>
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
