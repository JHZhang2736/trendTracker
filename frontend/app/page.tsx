"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { BarChart3, Brain, Bell, Database } from "lucide-react"
import { api, type HealthStatus } from "@/lib/api"

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [healthError, setHealthError] = useState(false)

  useEffect(() => {
    api
      .health()
      .then((data) => setHealth(data))
      .catch(() => setHealthError(true))
  }, [])

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
