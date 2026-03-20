"use client"

import { useEffect, useState } from "react"
import { TrendingUp, ExternalLink, Flame } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { api, type TrendItem } from "@/lib/api"
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

function TrendRow({ item, index }: { item: TrendItem; index: number }) {
  const rankDisplay = item.rank !== null ? item.rank + 1 : index + 1
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
      <Skeleton className="w-12 h-4" />
    </div>
  )
}

function PlatformCard({ slug }: { slug: string }) {
  const [items, setItems] = useState<TrendItem[]>([])
  const [loading, setLoading] = useState(true)
  const meta = getPlatformMeta(slug)

  useEffect(() => {
    api.trends
      .list(1, 50, slug)
      .then((res) => setItems(res.items))
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [slug])

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
              <TrendRow key={`${item.keyword}-${i}`} item={item} index={i} />
            ))
          )}
        </div>
      </CardContent>
    </Card>
  )
}

const PLATFORMS = Object.keys(PLATFORM_CONFIG)

export default function TrendsPage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <TrendingUp className="w-6 h-6" />
          趋势列表
        </h1>
        <p className="text-muted-foreground text-sm mt-1">近24小时各平台热词 Top 50</p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 xl:grid-cols-3">
        {PLATFORMS.map((slug) => (
          <PlatformCard key={slug} slug={slug} />
        ))}
      </div>
    </div>
  )
}
