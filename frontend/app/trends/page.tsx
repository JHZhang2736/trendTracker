"use client"

import { useEffect, useState, useCallback } from "react"
import { TrendingUp, TrendingDown, Minus, ExternalLink, Flame, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { api, type TrendItem, type VelocityItem } from "@/lib/api"
import { PLATFORM_CONFIG, getPlatformMeta } from "@/lib/platform-config"

function formatHeat(score: number | null): string {
  if (score === null) return "—"
  if (score >= 1_000_000) return `${(score / 1_000_000).toFixed(1)}M`
  if (score >= 1_000) return `${(score / 1_000).toFixed(0)}K`
  return String(score)
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  })
}

function VelocityBadge({ velocity, acceleration }: { velocity: number | null; acceleration: number | null }) {
  if (velocity === null || velocity === 0) {
    return (
      <span className="flex items-center gap-0.5 text-xs text-muted-foreground w-16 justify-end" title="velocity: 0%">
        <Minus className="w-3 h-3" />
        <span className="font-mono">0%</span>
      </span>
    )
  }

  const isUp = velocity > 0
  const Icon = isUp ? TrendingUp : TrendingDown
  const color = isUp ? "text-red-500" : "text-green-600"
  const absVal = Math.abs(velocity)
  const display = absVal >= 100 ? `${Math.round(absVal)}%` : `${absVal.toFixed(1)}%`

  let accelIndicator = ""
  if (acceleration !== null) {
    if (acceleration > 5) accelIndicator = " \u2191\u2191"
    else if (acceleration < -5) accelIndicator = " \u2193\u2193"
  }

  const title = `velocity: ${isUp ? "+" : ""}${velocity.toFixed(1)}%${acceleration !== null ? `, accel: ${acceleration.toFixed(1)}` : ""}`

  return (
    <span className={`flex items-center gap-0.5 text-xs font-mono w-16 justify-end ${color}`} title={title}>
      <Icon className="w-3 h-3 shrink-0" />
      <span>{isUp ? "+" : "-"}{display}{accelIndicator}</span>
    </span>
  )
}

function TrendRow({
  item,
  index,
  velocityData,
}: {
  item: TrendItem
  index: number
  velocityData?: VelocityItem
}) {
  const rankDisplay = index + 1
  const isHot = rankDisplay <= 3

  return (
    <div className="flex items-center gap-3 py-2.5 border-b last:border-0 hover:bg-muted/30 transition-colors px-3">
      <span
        className={`w-6 text-center text-sm font-bold shrink-0 ${
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
        <div className="flex items-center gap-1.5">
          {isHot && <Flame className="w-3 h-3 text-red-400 shrink-0" />}
          <span className="text-sm truncate">{item.keyword}</span>
        </div>
        <span className="text-xs text-muted-foreground">{formatTime(item.collected_at)}</span>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <VelocityBadge
          velocity={velocityData?.velocity ?? null}
          acceleration={velocityData?.acceleration ?? null}
        />
        <span className="text-xs font-mono text-muted-foreground w-12 text-right">
          {formatHeat(item.heat_score)}
        </span>
        {item.url ? (
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        ) : (
          <span className="w-3.5" />
        )}
      </div>
    </div>
  )
}

function TrendRowSkeleton() {
  return (
    <div className="flex items-center gap-3 py-2.5 border-b last:border-0 px-3">
      <Skeleton className="w-6 h-4 shrink-0" />
      <div className="flex-1 space-y-1">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-3 w-20" />
      </div>
      <Skeleton className="w-16 h-4" />
      <Skeleton className="w-12 h-4" />
    </div>
  )
}

function PlatformCard({
  slug,
  refreshKey,
  velocityMap,
}: {
  slug: string
  refreshKey: number
  velocityMap: Record<string, VelocityItem>
}) {
  const [items, setItems] = useState<TrendItem[]>([])
  const [loading, setLoading] = useState(true)
  const meta = getPlatformMeta(slug)

  useEffect(() => {
    let cancelled = false
    api.trends
      .list(1, 50, slug)
      .then((res) => { if (!cancelled) setItems(res.items) })
      .catch(() => { if (!cancelled) setItems([]) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true; setLoading(true) }
  }, [slug, refreshKey])

  return (
    <Card className="flex flex-col">
      <CardHeader className="pb-2 shrink-0">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <span
            className="inline-block w-2.5 h-2.5 rounded-full shrink-0"
            style={{ backgroundColor: meta.color }}
          />
          {meta.displayName}
          {!loading && (
            <span className="text-xs font-normal text-muted-foreground ml-auto">
              {items.length} 条
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0 flex-1 overflow-hidden">
        <div className="h-[600px] overflow-y-auto">
          {loading ? (
            Array.from({ length: 12 }).map((_, i) => <TrendRowSkeleton key={i} />)
          ) : items.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-muted-foreground gap-2">
              <TrendingUp className="w-8 h-8 opacity-20" />
              <p className="text-sm">暂无近24小时数据</p>
            </div>
          ) : (
            items.map((item, i) => (
              <TrendRow
                key={`${item.keyword}-${i}`}
                item={item}
                index={i}
                velocityData={velocityMap[`${slug}:${item.keyword}`]}
              />
            ))
          )}
        </div>
      </CardContent>
    </Card>
  )
}

const PLATFORMS = Object.keys(PLATFORM_CONFIG)

export default function TrendsPage() {
  const [refreshKey, setRefreshKey] = useState(0)
  const [refreshing, setRefreshing] = useState(false)
  const [velocityMap, setVelocityMap] = useState<Record<string, VelocityItem>>({})

  useEffect(() => {
    api.trends
      .velocity(undefined, 24, 200)
      .then((res) => {
        const map: Record<string, VelocityItem> = {}
        for (const item of res.items) {
          map[`${item.platform}:${item.keyword}`] = item
        }
        setVelocityMap(map)
      })
      .catch(() => setVelocityMap({}))
  }, [refreshKey])

  const handleRefresh = useCallback(async () => {
    setRefreshing(true)
    try {
      await api.post("/api/v1/collector/run", {})
      setRefreshKey((k) => k + 1)
    } finally {
      setRefreshing(false)
    }
  }, [])

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <TrendingUp className="w-6 h-6" />
            趋势列表
          </h1>
          <p className="text-muted-foreground text-sm mt-1">近24小时各平台热词 Top 50</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          disabled={refreshing}
          className="gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
          立即采集
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 xl:grid-cols-3">
        {PLATFORMS.map((slug) => (
          <PlatformCard key={slug} slug={slug} refreshKey={refreshKey} velocityMap={velocityMap} />
        ))}
      </div>
    </div>
  )
}
