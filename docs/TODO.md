# TrendTracker — 待办事项

> 最后更新：2026-03-20（#45 合并后）

---

## 🔴 高优先级（Bug / 核心功能缺失）

- [x] **定时采集不入库** — `collect_trends_job` 未调用 `run_all_collectors`，数据全丢（已修复 #43）

---

## 🟡 中优先级（前端空壳，后端已就绪）

- [x] **AI 洞察页** (`/ai`) — 已实现关键词分析 + 每日简报展示 + 生成按钮（#45）

- [x] **告警监控页** (`/alerts`) — 已实现规则列表 + 新建表单（#45）

- [x] **仪表盘统计卡片** — 已接入真实 API（热词总数、已采集平台数、今日简报、告警规则数）（#45）

- [x] **仪表盘数据源状态卡片** — 已根据近24小时数据实时反映各平台状态（#45）

---

## 🟢 低优先级（技术债）

- [ ] **`COLLECT_CRON` 环境变量无效** — `config.py` 有 `collect_cron` 字段，但 `scheduler.py` 硬编码 `IntervalTrigger(hours=1)`，该配置完全未被读取
  - 修复：`setup_scheduler` 中读取 `settings.collect_cron` 解析为 `CronTrigger`，或改用 `IntervalTrigger` 读取间隔分钟数

- [ ] **趋势列表页重复平台标签** — `frontend/app/trends/page.tsx` 有本地 `PLATFORM_LABELS` 字典，与 `frontend/lib/platform-config.ts` 重复，新增平台要改两处
  - 修复：改为 `import { getPlatformMeta } from "@/lib/platform-config"`

---

## 📋 PRD 规划中，未开始

- [ ] **F2.5 趋势历史折线图** — 单词热度随时间变化曲线（需要按 keyword + platform 查询历史数据）
- [ ] **F3.4 AI 自由对话** — 基于当前趋势数据与 AI 问答（需要 chat 接口 + 前端对话 UI）
- [ ] **F1.7 百度指数采集** — 需账号 Cookie，稳定性风险高，暂缓

---

## ⚙️ 数据源状态

| 平台 | 状态 | 备注 |
|------|------|------|
| 微博 | ✅ 正常 | 无需配置 |
| Google Trends | ✅ 正常 | 已更新 RSS 地址（#41），每次返回约 10 条 |
| TikTok | ⚙️ 需配置 | 设置 `TIKTOK_COOKIE` 后可用，参见 `.env.example` |
