"use client"

import { useEffect, useRef } from "react"
import type { HeatmapResponse } from "@/lib/api"

const PLATFORM_LABELS: Record<string, string> = {
  weibo: "微博",
  google: "Google",
  tiktok: "TikTok",
  baidu: "百度",
}

interface Props {
  data: HeatmapResponse
}

export function HeatmapChart({ data }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const chartRef = useRef<any>(null)

  useEffect(() => {
    let chart: typeof chartRef.current = null

    async function init() {
      if (!containerRef.current) return
      const echarts = await import("echarts")
      chart = echarts.init(containerRef.current, undefined, { renderer: "canvas" })
      chartRef.current = chart

      const platformLabels = data.platforms.map((p) => PLATFORM_LABELS[p] ?? p)

      const option = {
        tooltip: {
          position: "top",
          formatter: (params: { data: number[] }) => {
            const [pIdx, sIdx, value] = params.data
            const platform = platformLabels[pIdx] ?? String(pIdx)
            const slot = data.time_slots[sIdx] ?? String(sIdx)
            const heat =
              value >= 1_000_000
                ? `${(value / 1_000_000).toFixed(1)}M`
                : value >= 1_000
                  ? `${(value / 1_000).toFixed(0)}K`
                  : String(value)
            return `${platform} · ${slot}<br/>热度: <b>${heat}</b>`
          },
        },
        grid: { top: 20, right: 20, bottom: 60, left: 60 },
        xAxis: {
          type: "category",
          data: platformLabels,
          splitArea: { show: true },
          axisLabel: { fontSize: 12 },
        },
        yAxis: {
          type: "category",
          data: data.time_slots,
          splitArea: { show: true },
          axisLabel: { fontSize: 11 },
        },
        visualMap: {
          min: 0,
          max: data.max_heat || 1,
          calculable: true,
          orient: "horizontal",
          left: "center",
          bottom: 0,
          inRange: { color: ["#e0f2fe", "#0369a1"] },
          textStyle: { fontSize: 11 },
        },
        series: [
          {
            type: "heatmap",
            data: data.data,
            label: { show: false },
            emphasis: {
              itemStyle: { shadowBlur: 8, shadowColor: "rgba(0,0,0,0.3)" },
            },
          },
        ],
      }

      chart.setOption(option)
    }

    init()

    const observer = new ResizeObserver(() => chartRef.current?.resize())
    if (containerRef.current) observer.observe(containerRef.current)

    return () => {
      observer.disconnect()
      chart?.dispose()
    }
  }, [data])

  return <div ref={containerRef} style={{ width: "100%", height: 320 }} />
}
