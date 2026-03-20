"use client"

import { useState } from "react"
import { Brain, Sparkles, RefreshCw, Search } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { api, type AnalyzeResult, type BriefResponse } from "@/lib/api"

const SENTIMENT_CONFIG = {
  positive: { label: "正面", className: "bg-green-100 text-green-700 border-green-200" },
  negative: { label: "负面", className: "bg-red-100 text-red-700 border-red-200" },
  neutral:  { label: "中性", className: "bg-gray-100 text-gray-600 border-gray-200" },
}

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

function AnalyzeResultCard({ result }: { result: AnalyzeResult }) {
  const sentiment = SENTIMENT_CONFIG[result.sentiment] ?? SENTIMENT_CONFIG.neutral
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">{result.keyword}</CardTitle>
          <Badge variant="outline" className={sentiment.className}>
            {sentiment.label}
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground">
          {new Date(result.created_at).toLocaleString("zh-CN")}
          {result.model && <span className="ml-2 opacity-60">· {result.model}</span>}
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-1">商业洞察</p>
          <p className="text-sm leading-relaxed">{result.business_insight}</p>
        </div>
        {result.related_keywords.length > 0 && (
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">相关关键词</p>
            <div className="flex flex-wrap gap-1.5">
              {result.related_keywords.map((kw) => (
                <Badge key={kw} variant="secondary" className="text-xs">
                  {kw}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default function AIPage() {
  const [keyword, setKeyword] = useState("")
  const [analyzing, setAnalyzing] = useState(false)
  const [analyzeError, setAnalyzeError] = useState("")
  const [result, setResult] = useState<AnalyzeResult | null>(null)

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

  const handleAnalyze = async () => {
    if (!keyword.trim()) return
    setAnalyzing(true)
    setAnalyzeError("")
    try {
      const res = await api.ai.analyze(keyword.trim())
      setResult(res)
    } catch (e) {
      setAnalyzeError(e instanceof Error ? e.message : "分析失败，请稍后重试")
    } finally {
      setAnalyzing(false)
    }
  }

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
        <p className="text-muted-foreground mt-1 text-sm">关键词商业分析 · 每日趋势简报</p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Analyze panel */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">关键词分析</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex gap-2">
                <Input
                  placeholder="输入热词，例如：人工智能"
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleAnalyze()}
                  disabled={analyzing}
                />
                <Button onClick={handleAnalyze} disabled={analyzing || !keyword.trim()} className="gap-1.5 shrink-0">
                  <Search className={`w-4 h-4 ${analyzing ? "animate-pulse" : ""}`} />
                  {analyzing ? "分析中…" : "分析"}
                </Button>
              </div>
              {analyzeError && (
                <p className="text-sm text-destructive">{analyzeError}</p>
              )}
            </CardContent>
          </Card>

          {analyzing && (
            <Card>
              <CardContent className="pt-6 space-y-3">
                <Skeleton className="h-5 w-32" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-2/3" />
              </CardContent>
            </Card>
          )}

          {result && !analyzing && <AnalyzeResultCard result={result} />}
        </div>

        {/* Brief panel */}
        <BriefCard
          brief={brief}
          loading={briefLoading}
          onGenerate={handleGenerate}
          generating={generating}
        />
      </div>
    </div>
  )
}
