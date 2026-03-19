"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { BarChart3, Brain, Bell, Database } from "lucide-react"
import { api, type HealthStatus, type PlatformTrendItem } from "@/lib/api"
import { TopKeywordsChart } from "@/components/TopKeywordsChart"
import { getPlatformMeta } from "@/lib/platform-config"

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [healthError, setHealthError] = useState(false)
  const [platformTrends, setPlatformTrends] = useState<Record<string, PlatformTrendItem[]>>({})
  const [trendsLoading, setTrendsLoading] = useState(true)

  useEffect(() => {
    api
      .health()
      .then((data) => setHealth(data))
      .catch(() => setHealthError(true))

    api.trends
      .topByPlatform(10)
      .then((data) => setPlatformTrends(data.platforms))
      .catch(() => setPlatformTrends({}))
      .finally(() => setTrendsLoading(false))
  }, [])

  const platformEntries = Object.entries(platformTrends)

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

      {/* Status Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">数据采集</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">—</div>
            <p className="text-xs text-muted-foreground mt-1">等待首次采集</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">热词总数</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">—</div>
            <p className="text-xs text-muted-foreground mt-1">暂无数据</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">AI 分析</CardTitle>
            <Brain className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">—</div>
            <p className="text-xs text-muted-foreground mt-1">暂无分析记录</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">告警规则</CardTitle>
            <Bell className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">—</div>
            <p className="text-xs text-muted-foreground mt-1">暂未配置</p>
          </CardContent>
        </Card>
      </div>

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

      {/* Platform Status */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">数据源状态</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {["微博热搜", "Google Trends", "TikTok", "百度指数"].map((platform) => (
              <Badge key={platform} variant="secondary">
                {platform} · 待接入
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
