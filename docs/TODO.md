# TrendTracker — 待办事项

> 最后更新：2026-03-20

---

## 🔴 高优先级（Bug / 核心功能缺失）

- [x] **定时采集不入库** — `collect_trends_job` 未调用 `run_all_collectors`，数据全丢（已修复 #43）

---

## 🟡 中优先级（前端空壳，后端已就绪）

- [ ] **AI 洞察页** (`/ai`) — 后端 `/api/v1/ai/analyze` 和 `/brief` 已完整实现，前端仅 "Coming soon"
  - 关键词输入 → AI 分析（商业建议 + 情感极性 + 相关词）
  - 展示最新每日简报
  - 手动触发生成简报按钮

- [ ] **告警监控页** (`/alerts`) — 后端 CRUD + 邮件触发已完整实现，前端仅 "Coming soon"
  - 告警规则列表（关键词 + 阈值 + 邮件）
  - 新建规则表单
  - 告警日志展示

- [ ] **仪表盘统计卡片** — 4 张卡片（采集次数、热词总数、AI 分析数、告警规则数）全部显示 `—`，未接 API
  - `GET /api/v1/trends` 的 `total` 字段可用于热词总数
  - `GET /api/v1/ai/insights` 可用于 AI 分析数
  - `GET /api/v1/alerts/rules` 可用于告警规则数

- [ ] **仪表盘数据源状态卡片** — 硬编码 "待接入"，应实时反映各平台状态（有无近期数据）

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
