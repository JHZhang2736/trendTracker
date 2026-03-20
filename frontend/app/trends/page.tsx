"use client"

import { useEffect, useState } from "react"
import { TrendingUp, RefreshCw, ExternalLink, Flame } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { api, TrendItem } from "@/lib/api"
import { getPlatformMeta } from "@/lib/platform-config"

function formatHeat(score: number | null): string {
  if (score === null) return "—"
  if (score >= 1_000_000) return `${(score / 1_000_000).toFixed(1)}M`
  if (score >= 1_000) return `${(score / 1_000).toFixed(0)}K`
  return String(score)
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })
}

function TrendRow({ item, index }: { item: TrendItem; index: number }) {
  const rankDisplay = item.rank !== null ? item.rank + 1 : index + 1
  const isHot = rankDisplay <= 3

  return (
    <div className="flex items-center gap-4 py-3 border-b last:border-0 hover:bg-muted/30 transition-colors px-4">
      <span
        className={`w-8 text-center text-sm font-bold shrink-0 ${
          rankDisplay === 1
            ? "text-red-500"
            : rankDisplay === 2
              ? "text-orange-400"
              : rankDisplay === 3
                ? "text-yellow-500"
                : "text-muted-foreground"
        }`}
      >
        {rankDisplay}
      </span>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          {isHot && <Flame className="w-3.5 h-3.5 text-red-400 shrink-0" />}
          <span className="font-medium text-sm truncate">{item.keyword}</span>
        </div>
        <div className="flex items-center gap-2 mt-0.5">
          <Badge variant="secondary" className="text-xs py-0 h-4">
            {getPlatformMeta(item.platform).displayName}
          </Badge>
          <span className="text-xs text-muted-foreground">{formatTime(item.collected_at)}</span>
        </div>
      </div>

      <div className="flex items-center gap-3 shrink-0">
        <span className="text-sm font-mono text-muted-foreground w-16 text-right">
          {formatHeat(item.heat_score)}
        </span>
        {item.url && (
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <ExternalLink className="w-4 h-4" />
          </a>
        )}
      </div>
    </div>
  )
}

function TrendRowSkeleton() {
  return (
    <div className="flex items-center gap-4 py-3 border-b last:border-0 px-4">
      <Skeleton className="w-8 h-4 shrink-0" />
      <div className="flex-1 space-y-1.5">
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-3 w-24" />
      </div>
      <Skeleton className="w-16 h-4" />
    </div>
  )
}

export default function TrendsPage() {
  const [items, setItems] = useState<TrendItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const pageSize = 50

  const fetchTrends = async (p: number) => {
    setLoading(true)
    try {
      const res = await api.trends.list(p, pageSize)
      setItems(res.items)
      setTotal(res.total)
      setPage(res.page)
    } catch {
      // silently ignore — backend may not be running
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTrends(1)
  }, [])

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      await api.post("/api/v1/collector/run", {})
      await fetchTrends(1)
    } finally {
      setRefreshing(false)
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <TrendingUp className="w-6 h-6" />
            趋势列表
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            共 {total} 条热词记录
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          disabled={refreshing || loading}
          className="gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
          立即采集
        </Button>
      </div>

      {/* Trends Card */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">热词排行</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            Array.from({ length: 10 }).map((_, i) => <TrendRowSkeleton key={i} />)
          ) : items.length === 0 ? (
            <div className="py-16 text-center text-muted-foreground">
              <TrendingUp className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p className="text-sm">暂无数据，点击「立即采集」获取热词</p>
            </div>
          ) : (
            items.map((item, i) => <TrendRow key={`${item.platform}-${item.keyword}-${i}`} item={item} index={i} />)
          )}
        </CardContent>
      </Card>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchTrends(page - 1)}
            disabled={page <= 1 || loading}
          >
            上一页
          </Button>
          <span className="text-sm text-muted-foreground">
            {page} / {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchTrends(page + 1)}
            disabled={page >= totalPages || loading}
          >
            下一页
          </Button>
        </div>
      )}
    </div>
  )
}
