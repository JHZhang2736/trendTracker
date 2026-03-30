export interface PlatformMeta {
  displayName: string
  color: string
  category: string
}

/**
 * Central platform display configuration.
 * Add one entry here when registering a new platform in the backend.
 * Keys must match the `platform` slug used in the backend collectors.
 */
export const PLATFORM_CONFIG: Record<string, PlatformMeta> = {
  // 综合热搜/新闻
  weibo: { displayName: "微博热搜", color: "#e2231a", category: "热搜/新闻" },
  douyin: { displayName: "抖音热榜", color: "#000000", category: "热搜/新闻" },
  toutiao: { displayName: "今日头条", color: "#f85959", category: "热搜/新闻" },
  "qq-news": { displayName: "腾讯新闻", color: "#1da1f2", category: "热搜/新闻" },
  "netease-news": { displayName: "网易新闻", color: "#d43c33", category: "热搜/新闻" },
  "sina-news": { displayName: "新浪新闻", color: "#ff8c00", category: "热搜/新闻" },
  nytimes: { displayName: "纽约时报", color: "#1a1a1a", category: "热搜/新闻" },
  // 社区/讨论
  zhihu: { displayName: "知乎热榜", color: "#0066ff", category: "社区/讨论" },
  "zhihu-daily": { displayName: "知乎日报", color: "#0084ff", category: "社区/讨论" },
  tieba: { displayName: "百度贴吧", color: "#4e6ef2", category: "社区/讨论" },
  hupu: { displayName: "虎扑热帖", color: "#e21f2c", category: "社区/讨论" },
  "douban-group": { displayName: "豆瓣小组", color: "#00b51d", category: "社区/讨论" },
  // 科技/互联网
  "36kr": { displayName: "36氪", color: "#0478e1", category: "科技/互联网" },
  producthunt: { displayName: "Product Hunt", color: "#da552f", category: "科技/互联网" },
  // 开发者
  github: { displayName: "GitHub Trending", color: "#24292e", category: "开发者" },
  hackernews: { displayName: "Hacker News", color: "#ff6600", category: "开发者" },
  // 视频/娱乐
  bilibili: { displayName: "B站热榜", color: "#fb7299", category: "视频/娱乐" },
  kuaishou: { displayName: "快手热榜", color: "#ff4906", category: "视频/娱乐" },
  // 购物/消费
  smzdm: { displayName: "什么值得买", color: "#e4393c", category: "购物/消费" },
  coolapk: { displayName: "酷安", color: "#11ab60", category: "购物/消费" },
  // 游戏
  yystv: { displayName: "游研社", color: "#6c5ce7", category: "游戏" },
}

export function getPlatformMeta(platform: string): PlatformMeta {
  return (
    PLATFORM_CONFIG[platform] ?? {
      displayName: platform,
      color: "#6b7280",
      category: "其他",
    }
  )
}
