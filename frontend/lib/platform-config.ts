export interface PlatformMeta {
  displayName: string
  color: string
}

/**
 * Central platform display configuration.
 * Add one entry here when registering a new platform in the backend.
 * Keys must match the `platform` slug used in the backend collectors.
 */
export const PLATFORM_CONFIG: Record<string, PlatformMeta> = {
  weibo: { displayName: "微博热搜", color: "#e2231a" },
  google: { displayName: "Google 趋势", color: "#4285f4" },
  tiktok: { displayName: "TikTok", color: "#010101" },
  // 新增平台在此添加一行 ↑
}

export function getPlatformMeta(platform: string): PlatformMeta {
  return (
    PLATFORM_CONFIG[platform] ?? {
      displayName: platform,
      color: "#6b7280",
    }
  )
}
