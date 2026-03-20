"use client"

import { useEffect, useState } from "react"
import { Bell, Plus, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { api, type AlertRule } from "@/lib/api"

function formatHeat(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`
  return String(v)
}

function RuleRow({ rule }: { rule: AlertRule }) {
  return (
    <div className="flex items-center gap-4 py-3 border-b last:border-0 px-4">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium text-sm">{rule.keyword}</span>
          <Badge variant={rule.is_active ? "default" : "secondary"} className="text-xs">
            {rule.is_active ? "监控中" : "已停用"}
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground mt-0.5">
          阈值：{formatHeat(rule.threshold)}
          {rule.notify_email && <span className="ml-3">通知：{rule.notify_email}</span>}
        </p>
      </div>
      <span className="text-xs text-muted-foreground shrink-0">
        {new Date(rule.created_at).toLocaleDateString("zh-CN")}
      </span>
    </div>
  )
}

export default function AlertsPage() {
  const [rules, setRules] = useState<AlertRule[]>([])
  const [loading, setLoading] = useState(true)

  const [keyword, setKeyword] = useState("")
  const [threshold, setThreshold] = useState("")
  const [email, setEmail] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState("")

  const loadRules = async () => {
    try {
      const res = await api.alerts.listRules()
      setRules(res.items)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadRules() }, [])

  const handleCreate = async () => {
    setFormError("")
    if (!keyword.trim()) { setFormError("请输入关键词"); return }
    const t = parseFloat(threshold)
    if (isNaN(t) || t <= 0) { setFormError("阈值须为正数"); return }
    if (!email.trim()) { setFormError("请输入通知邮箱"); return }

    setSubmitting(true)
    try {
      const rule = await api.alerts.createRule(keyword.trim(), t, email.trim())
      setRules((prev) => [rule, ...prev])
      setKeyword("")
      setThreshold("")
      setEmail("")
    } catch (e) {
      setFormError(e instanceof Error ? e.message : "创建失败，请重试")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Bell className="w-6 h-6" />
          告警监控
        </h1>
        <p className="text-muted-foreground mt-1 text-sm">关键词热度超阈值时自动发送邮件通知</p>
      </div>

      {/* Create form */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Plus className="w-4 h-4" />
            新建监控规则
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">关键词</label>
              <Input
                placeholder="例如：人工智能"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                disabled={submitting}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">热度阈值</label>
              <Input
                type="number"
                placeholder="例如：10000"
                value={threshold}
                onChange={(e) => setThreshold(e.target.value)}
                disabled={submitting}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">通知邮箱</label>
              <Input
                type="email"
                placeholder="your@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={submitting}
              />
            </div>
          </div>
          {formError && <p className="text-sm text-destructive">{formError}</p>}
          <Button onClick={handleCreate} disabled={submitting} size="sm" className="gap-1.5">
            <Plus className="w-3.5 h-3.5" />
            {submitting ? "创建中…" : "创建规则"}
          </Button>
        </CardContent>
      </Card>

      {/* Rules list */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">
            监控规则
            {!loading && (
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                共 {rules.length} 条
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="px-4 py-3 space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="space-y-1.5">
                  <Skeleton className="h-4 w-40" />
                  <Skeleton className="h-3 w-56" />
                </div>
              ))}
            </div>
          ) : rules.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground">
              <Trash2 className="w-8 h-8 mx-auto mb-2 opacity-20" />
              <p className="text-sm">暂无监控规则，上方创建第一条</p>
            </div>
          ) : (
            rules.map((rule) => <RuleRow key={rule.id} rule={rule} />)
          )}
        </CardContent>
      </Card>
    </div>
  )
}
