"use client"

import { useCallback, useState, useEffect } from "react"
import { Search, RefreshCw, ExternalLink, TrendingUp, AlertTriangle, Lightbulb, Zap } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { api, type DeepAnalysisResponse } from "@/lib/api"

const sentimentConfig = {
  positive: { label: "积极", className: "bg-green-100 text-green-700" },
  negative: { label: "消极", className: "bg-red-100 text-red-700" },
  neutral: { label: "中性", className: "bg-gray-100 text-gray-600" },
} as const

function formatTime(iso: string | null) {
  if (!iso) return "—"
  const d = new Date(iso)
  return d.toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })
}

function AnalysisCard({ item }: { item: DeepAnalysisResponse }) {
  const [expanded, setExpanded] = useState(false)
  const sentiment = sentimentConfig[item.deep_analysis.sentiment] ?? sentimentConfig.neutral

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader
        className="pb-2 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base">{item.keyword}</CardTitle>
          <div className="flex items-center gap-2 shrink-0">
            <Badge variant="outline" className={sentiment.className}>
              {sentiment.label}
            </Badge>
            {item.analysis_type === "auto" && (
              <Badge variant="secondary" className="text-xs">
                自动
              </Badge>
            )}
          </div>
        </div>
        <p className="text-xs text-muted-foreground">
          {formatTime(item.created_at)} · {item.search_results_count} 条搜索结果 · {item.model}
        </p>
      </CardHeader>

      <CardContent className="space-y-3">
        <div className="flex items-start gap-2">
          <Lightbulb className="w-4 h-4 mt-0.5 text-blue-500 shrink-0" />
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-0.5">背景</p>
            <p className="text-sm">{item.deep_analysis.background || "—"}</p>
          </div>
        </div>

        {item.deep_analysis.opportunities.length > 0 && (
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-1.5">商业机会</p>
            <div className="space-y-2">
              {item.deep_analysis.opportunities.slice(0, expanded ? undefined : 2).map((opp, i) => (
                <div key={i} className="flex items-start gap-2">
                  <TrendingUp className="w-3.5 h-3.5 mt-0.5 text-green-500 shrink-0" />
                  <div>
                    <span className="text-xs font-medium text-green-700 bg-green-50 px-1.5 py-0.5 rounded">
                      {opp.angle}
                    </span>
                    <p className="text-sm mt-0.5">{opp.idea}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {expanded && (
          <>
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 mt-0.5 text-amber-500 shrink-0" />
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-0.5">风险</p>
                <p className="text-sm">{item.deep_analysis.risk || "—"}</p>
              </div>
            </div>

            <div className="flex items-start gap-2">
              <Zap className="w-4 h-4 mt-0.5 text-purple-500 shrink-0" />
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-0.5">建议行动</p>
                <p className="text-sm">{item.deep_analysis.action || "—"}</p>
              </div>
            </div>

            {item.source_urls.length > 0 && (
              <div className="pt-2 border-t">
                <p className="text-xs font-medium text-muted-foreground mb-1">信息来源</p>
                <div className="flex flex-wrap gap-1">
                  {item.source_urls.map((url, i) => (
                    <a
                      key={i}
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
                    >
                      <ExternalLink className="w-3 h-3" />
                      来源{i + 1}
                    </a>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          {expanded ? "收起" : "展开详情"}
        </button>
      </CardContent>
    </Card>
  )
}

export default function DeepAnalysisPage() {
  const [analyses, setAnalyses] = useState<DeepAnalysisResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [keyword, setKeyword] = useState("")
  const [analyzing, setAnalyzing] = useState(false)
  const [error, setError] = useState("")

  const loadAnalyses = useCallback(async () => {
    try {
      const data = await api.ai.listDeepAnalyses()
      setAnalyses(data)
    } catch {
      /* empty */
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadAnalyses()
  }, [loadAnalyses])

  const handleAnalyze = async () => {
    const kw = keyword.trim()
    if (!kw) return
    setAnalyzing(true)
    setError("")
    try {
      await api.ai.deepAnalyze(kw)
      setKeyword("")
      await loadAnalyses()
    } catch (e) {
      setError(e instanceof Error ? e.message : "分析失败")
    } finally {
      setAnalyzing(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">深度分析</h1>
        <p className="text-muted-foreground mt-1">
          网络搜索 + AI 生成结构化商业分析报告
        </p>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-2">
            <Input
              placeholder="输入关键词进行深度分析..."
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !analyzing && handleAnalyze()}
              disabled={analyzing}
            />
            <Button onClick={handleAnalyze} disabled={analyzing || !keyword.trim()}>
              {analyzing ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Search className="w-4 h-4" />
              )}
              <span className="ml-1">{analyzing ? "分析中..." : "分析"}</span>
            </Button>
          </div>
          {error && <p className="text-sm text-destructive mt-2">{error}</p>}
          {analyzing && (
            <p className="text-sm text-muted-foreground mt-2">
              正在搜索网络并生成分析报告，请稍候...
            </p>
          )}
        </CardContent>
      </Card>

      {loading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-5 w-32" />
                <Skeleton className="h-3 w-48 mt-1" />
              </CardHeader>
              <CardContent className="space-y-2">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : analyses.length === 0 ? (
        <Card>
          <CardContent className="pt-6 text-center text-muted-foreground">
            <Search className="w-10 h-10 mx-auto mb-2 opacity-30" />
            <p>暂无深度分析报告</p>
            <p className="text-sm mt-1">输入关键词手动触发，或等待采集后自动分析</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {analyses.map((item) => (
            <AnalysisCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  )
}
