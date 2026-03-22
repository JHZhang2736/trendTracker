"use client"

import { useState } from "react"
import { Brain, Sparkles, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { api, type BriefResponse } from "@/lib/api"

function BriefCard({
  brief,
  loading,
  onGenerate,
  generating,
}: {
  brief: BriefResponse | null
  loading: boolean
  onGenerate: () => void
  generating: boolean
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-yellow-500" />
          每日趋势简报
        </CardTitle>
        <Button
          size="sm"
          variant="outline"
          onClick={onGenerate}
          disabled={generating}
          className="gap-1.5"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${generating ? "animate-spin" : ""}`} />
          {generating ? "生成中…" : "生成简报"}
        </Button>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </div>
        ) : brief ? (
          <div className="space-y-2">
            <p className="text-xs text-muted-foreground">
              {brief.date}
              {brief.model && <span className="ml-2 opacity-60">· {brief.model}</span>}
            </p>
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{brief.content}</p>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground py-4 text-center">
            暂无简报，点击「生成简报」创建今日摘要
          </p>
        )}
      </CardContent>
    </Card>
  )
}

export default function AIPage() {
  const [brief, setBrief] = useState<BriefResponse | null>(null)
  const [briefLoading, setBriefLoading] = useState(true)
  const [generating, setGenerating] = useState(false)

  // Load latest brief on mount
  useState(() => {
    api.ai
      .latestBrief()
      .then(setBrief)
      .catch(() => setBrief(null))
      .finally(() => setBriefLoading(false))
  })

  const handleGenerate = async () => {
    setGenerating(true)
    try {
      const res = await api.ai.generateBrief()
      setBrief(res)
    } catch {
      // silently ignore
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Brain className="w-6 h-6" />
          AI 洞察
        </h1>
        <p className="text-muted-foreground mt-1 text-sm">每日趋势简报 · 深度分析</p>
      </div>

      <BriefCard
        brief={brief}
        loading={briefLoading}
        onGenerate={handleGenerate}
        generating={generating}
      />
    </div>
  )
}
