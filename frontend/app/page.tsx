"use client"

import { useEffect, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { BarChart3, Brain, Bell, Database, Zap } from "lucide-react"
import { api, type HealthStatus, type PlatformTrendItem, type BriefResponse, type SignalItem } from "@/lib/api"
import { TopKeywordsChart } from "@/components/TopKeywordsChart"
import { getPlatformMeta } from "@/lib/platform-config"

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [healthError, setHealthError] = useState(false)

  const [totalTrends, setTotalTrends] = useState<number | null>(null)
  const [alertCount, setAlertCount] = useState<number | null>(null)
  const [brief, setBrief] = useState<BriefResponse | null>(null)

  const [platformTrends, setPlatformTrends] = useState<Record<string, PlatformTrendItem[]>>({})
  const [trendsLoading, setTrendsLoading] = useState(true)

  const [signals, setSignals] = useState<SignalItem[]>([])
  const [signalsLoading, setSignalsLoading] = useState(true)

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealthError(true))

    api.trends
      .count()
      .then((d) => setTotalTrends(d.total))
      .catch(() => setTotalTrends(null))

    api.alerts
      .listRules()
      .then((d) => setAlertCount(d.items.length))
      .catch(() => setAlertCount(null))

    api.ai
      .latestBrief()
      .then(setBrief)
      .catch(() => setBrief(null))

    api.trends
      .topByPlatform(10)
      .then((d) => setPlatformTrends(d.platforms))
      .catch(() => setPlatformTrends({}))
      .finally(() => setTrendsLoading(false))

    api.signals
      .recent(24, 20)
      .then((d) => setSignals(d.items))
      .catch(() => setSignals([]))
      .finally(() => setSignalsLoading(false))
  }, [])

  const platformEntries = Object.entries(platformTrends)
  const activePlatforms = platformEntries.map(([p]) => p)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">仪表盘</h1>
        <p className="text-muted-foreground mt-1">全网趋势概览</p>
      </div>

      {/* Backend Status */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium">后端服务</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center gap-3">
          {health ? (
            <>
              <Badge variant="default" className="bg-green-500 hover:bg-green-500">
                {health.status === "ok" ? "正常" : health.status}
              </Badge>
              <span className="text-xs text-muted-foreground">v{health.version}</span>
            </>
          ) : healthError ? (
            <Badge variant="destructive">离线</Badge>
          ) : (
            <span className="text-xs text-muted-foreground">连接中…</span>
          )}
        </CardContent>
      </Card>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">热词总数</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {totalTrends === null ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <div className="text-2xl font-bold">{totalTrends.toLocaleString()}</div>
            )}
            <p className="text-xs text-muted-foreground mt-1">数据库历史记录</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">已采集平台</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {trendsLoading ? (
              <Skeleton className="h-8 w-12" />
            ) : (
              <div className="text-2xl font-bold">{activePlatforms.length}</div>
            )}
            <p className="text-xs text-muted-foreground mt-1">近24小时有数据</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">今日简报</CardTitle>
            <Brain className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {brief ? (
              <div className="text-2xl font-bold">{brief.date}</div>
            ) : (
              <div className="text-2xl font-bold text-muted-foreground">—</div>
            )}
            <p className="text-xs text-muted-foreground mt-1">
              {brief ? "AI 简报已生成" : "尚未生成今日简报"}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">告警规则</CardTitle>
            <Bell className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {alertCount === null ? (
              <Skeleton className="h-8 w-12" />
            ) : (
              <div className="text-2xl font-bold">{alertCount}</div>
            )}
            <p className="text-xs text-muted-foreground mt-1">活跃监控规则</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">趋势信号</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {signalsLoading ? (
              <Skeleton className="h-8 w-12" />
            ) : (
              <div className="text-2xl font-bold">{signals.length}</div>
            )}
            <p className="text-xs text-muted-foreground mt-1">近24小时检测到</p>
          </CardContent>
        </Card>
      </div>

      {/* Trend Signals */}
      {signalsLoading ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Zap className="h-4 w-4" />
              趋势信号（近24小时）
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Skeleton className="w-full h-32" />
          </CardContent>
        </Card>
      ) : signals.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Zap className="h-4 w-4" />
              趋势信号（近24小时）
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {signals.map((sig) => {
                const meta = getPlatformMeta(sig.platform)
                const typeLabel =
                  sig.signal_type === "rank_jump"
                    ? "排名跃升"
                    : sig.signal_type === "new_entry"
                      ? "新面孔"
                      : "热度突增"
                const typeColor =
                  sig.signal_type === "rank_jump"
                    ? "bg-blue-100 text-blue-800"
                    : sig.signal_type === "new_entry"
                      ? "bg-green-100 text-green-800"
                      : "bg-red-100 text-red-800"
                return (
                  <div
                    key={sig.id}
                    className="flex items-center gap-3 rounded-md border px-3 py-2 text-sm"
                  >
                    <Badge variant="outline" className={typeColor}>
                      {typeLabel}
                    </Badge>
                    <span
                      className="inline-block w-2 h-2 rounded-full shrink-0"
                      style={{ backgroundColor: meta.color }}
                    />
                    <span className="font-medium truncate">{sig.keyword}</span>
                    <span className="text-muted-foreground text-xs ml-auto shrink-0">
                      {sig.description}
                    </span>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      ) : null}

      {/* Per-Platform Top Keywords */}
      {trendsLoading ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">热词排行（近24小时 · 收敛评分）</CardTitle>
          </CardHeader>
          <CardContent>
            <Skeleton className="w-full h-80" />
          </CardContent>
        </Card>
      ) : platformEntries.length > 0 ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 xl:grid-cols-3">
          {platformEntries.map(([platform, items]) => {
            const meta = getPlatformMeta(platform)
            return (
              <Card key={platform}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <span
                      className="inline-block w-2.5 h-2.5 rounded-full"
                      style={{ backgroundColor: meta.color }}
                    />
                    {meta.displayName}
                    <span className="text-xs font-normal text-muted-foreground ml-auto">
                      收敛评分 0–100
                    </span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <TopKeywordsChart items={items} color={meta.color} />
                </CardContent>
              </Card>
            )
          })}
        </div>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">热词排行（近24小时 · 收敛评分）</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-48 flex items-center justify-center text-muted-foreground text-sm">
              暂无数据，请先在趋势列表页点击「立即采集」
            </div>
          </CardContent>
        </Card>
      )}

    </div>
  )
}
