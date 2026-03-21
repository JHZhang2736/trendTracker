"use client"

import { useEffect, useRef } from "react"
import type { PlatformTrendItem } from "@/lib/api"

interface Props {
  items: PlatformTrendItem[]
  color?: string
}

function formatHeat(v: number | null): string {
  if (v === null) return "0"
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`
  return String(v)
}

export function TopKeywordsChart({ items, color }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!containerRef.current || items.length === 0) return

    let chart: ReturnType<typeof import("echarts")["init"]> | null = null

    async function init() {
      if (!containerRef.current) return
      const echarts = await import("echarts")

      // Show top 15, sorted ascending so highest is at top
      const display = [...items].slice(0, 15).reverse()

      chart = echarts.init(containerRef.current, undefined, { renderer: "canvas" })
      chart.setOption({
        tooltip: {
          trigger: "axis",
          axisPointer: { type: "shadow" },
          formatter: (params: { name: string; value: number }[]) => {
            const p = params[0]
            const item = display.find((d) => d.keyword === p.name)
            const heat = formatHeat(item?.heat_score ?? null)
            return [
              `<b>${p.name}</b>`,
              `收敛评分：${p.value.toFixed(1)}`,
              heat !== "0" ? `热度：${heat}` : "",
            ]
              .filter(Boolean)
              .join("<br/>")
          },
        },
        grid: { top: 8, right: 80, bottom: 8, left: 8, containLabel: true },
        xAxis: {
          type: "value",
          max: 100,
          axisLabel: { show: false },
          splitLine: { lineStyle: { color: "#f0f0f0" } },
        },
        yAxis: {
          type: "category",
          data: display.map((d) => d.keyword),
          axisLabel: {
            fontSize: 12,
            width: 120,
            overflow: "truncate",
          },
        },
        series: [
          {
            type: "bar",
            data: display.map((d) => ({
              value: d.convergence_score,
              itemStyle: {
                color: color ?? (
                  d.convergence_score >= 70
                    ? "#ef4444"
                    : d.convergence_score >= 40
                    ? "#f97316"
                    : "#3b82f6"
                ),
                borderRadius: [0, 4, 4, 0],
              },
            })),
            label: {
              show: true,
              position: "right",
              formatter: (p: { value: number }) => p.value.toFixed(1),
              fontSize: 11,
              color: "#6b7280",
            },
          },
        ],
      })
    }

    init()

    const observer = new ResizeObserver(() => chart?.resize())
    if (containerRef.current) observer.observe(containerRef.current)

    return () => {
      observer.disconnect()
      chart?.dispose()
    }
  }, [items, color])

  return <div ref={containerRef} style={{ width: "100%", height: Math.max(240, items.length * 28) }} />
}
