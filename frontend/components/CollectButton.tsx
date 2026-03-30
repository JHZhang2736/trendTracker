"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { RefreshCw, CheckCircle, XCircle, ChevronDown, ChevronUp, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { getPlatformMeta } from "@/lib/platform-config"

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

interface CollectEvent {
  stage: string
  message: string
  platform?: string
  count?: number
  error?: string
  records_count?: number
  platforms?: { platform: string; count: number; error: string | null }[]
  total?: number
  relevant?: number
  analyzed?: number
}

export function CollectButton() {
  const [collecting, setCollecting] = useState(false)
  const [logs, setLogs] = useState<CollectEvent[]>([])
  const [done, setDone] = useState(false)
  const [panelVisible, setPanelVisible] = useState(false)
  const [collapsed, setCollapsed] = useState(false)
  const logsEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = useCallback(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [])

  // auto-scroll when new logs arrive
  useEffect(() => {
    if (logs.length > 0 && !collapsed) {
      scrollToBottom()
    }
  }, [logs.length, collapsed, scrollToBottom])

  const handleCollect = async () => {
    setCollecting(true)
    setLogs([])
    setDone(false)
    setPanelVisible(true)
    setCollapsed(false)
    try {
      const res = await fetch(`${BASE_URL}/api/v1/collector/run-stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      })
      if (!res.ok || !res.body) {
        setLogs([{ stage: "error", message: `请求失败: ${res.status}` }])
        return
      }
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ""
      while (true) {
        const { done: streamDone, value } = await reader.read()
        if (streamDone) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split("\n\n")
        buffer = lines.pop() ?? ""
        for (const chunk of lines) {
          const dataLine = chunk.replace(/^data: /, "").trim()
          if (!dataLine) continue
          try {
            const event: CollectEvent = JSON.parse(dataLine)
            setLogs((prev) => [...prev, event])
            if (event.stage === "done") {
              setDone(true)
            }
          } catch {
            // ignore malformed events
          }
        }
      }
    } catch {
      setLogs((prev) => [...prev, { stage: "error", message: "连接失败" }])
    } finally {
      setCollecting(false)
    }
  }

  const lastLog = logs[logs.length - 1]

  return (
    <>
      <Button
        size="sm"
        variant="outline"
        onClick={handleCollect}
        disabled={collecting}
        className="w-full gap-2"
      >
        <RefreshCw className={`w-4 h-4 ${collecting ? "animate-spin" : ""}`} />
        {collecting ? "采集中..." : "立即采集"}
      </Button>

      {/* 右下角悬浮进度面板 */}
      {panelVisible && (
        <div className="fixed bottom-4 right-4 z-50 w-80 rounded-lg border bg-background shadow-lg">
          {/* 标题栏 */}
          <div
            className="flex items-center justify-between px-3 py-2 border-b cursor-pointer select-none"
            onClick={() => setCollapsed((c) => !c)}
          >
            <div className="flex items-center gap-2 text-sm font-medium">
              {collecting ? (
                <RefreshCw className="w-3.5 h-3.5 text-blue-500 animate-spin" />
              ) : done ? (
                <CheckCircle className="w-3.5 h-3.5 text-green-500" />
              ) : (
                <XCircle className="w-3.5 h-3.5 text-destructive" />
              )}
              <span>{collecting ? "采集中..." : done ? "采集完成" : "采集失败"}</span>
            </div>
            <div className="flex items-center gap-1">
              {collapsed ? (
                <ChevronUp className="w-4 h-4 text-muted-foreground" />
              ) : (
                <ChevronDown className="w-4 h-4 text-muted-foreground" />
              )}
              {!collecting && (
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    setPanelVisible(false)
                  }}
                  className="ml-1 rounded p-0.5 hover:bg-muted"
                >
                  <X className="w-3.5 h-3.5 text-muted-foreground" />
                </button>
              )}
            </div>
          </div>

          {/* 日志区域 */}
          {!collapsed && (
            <div className="p-3 space-y-1.5 max-h-60 overflow-y-auto">
              {logs.length === 0 && collecting && (
                <p className="text-xs text-muted-foreground">正在连接...</p>
              )}
              {logs.map((log, i) => (
                <div key={i} className="flex items-start gap-2 text-xs">
                  <span className="shrink-0 mt-0.5">
                    {log.stage === "done" ? (
                      <CheckCircle className="w-3 h-3 text-green-500" />
                    ) : log.stage === "error" || log.error ? (
                      <XCircle className="w-3 h-3 text-destructive" />
                    ) : done || i < logs.length - 1 ? (
                      <CheckCircle className="w-3 h-3 text-muted-foreground" />
                    ) : (
                      <RefreshCw className="w-3 h-3 text-blue-500 animate-spin" />
                    )}
                  </span>
                  <span
                    className={
                      log.stage === "done"
                        ? "font-medium text-green-600"
                        : log.error
                          ? "text-destructive"
                          : "text-muted-foreground"
                    }
                  >
                    {log.message}
                  </span>
                  {log.stage === "collecting" && log.platform && !log.error && (
                    <Badge variant="secondary" className="text-[10px] ml-auto px-1 py-0">
                      {getPlatformMeta(log.platform).displayName} +{log.count}
                    </Badge>
                  )}
                </div>
              ))}
              <div ref={logsEndRef} />
            </div>
          )}

          {/* 折叠时显示最新一条 */}
          {collapsed && lastLog && (
            <div className="px-3 py-2 text-xs text-muted-foreground truncate">
              {lastLog.message}
            </div>
          )}
        </div>
      )}
    </>
  )
}
