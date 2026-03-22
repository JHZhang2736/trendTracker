# 技术文档
# TrendTracker — 架构设计与实现说明

**文档版本**: v0.4
**最后更新**: 2026-03-22

---

## 1. 技术栈

| 层级 | 技术 | 版本 | 说明 |
|------|------|------|------|
| 前端框架 | Next.js App Router | 16.2 | 全 Client Component，useEffect 拉数据 |
| 前端样式 | Tailwind CSS | v4 | |
| 前端组件库 | shadcn/ui（基于 **@base-ui/react**） | — | 注意：不是 Radix UI，API 有差异 |
| 前端图表 | ECharts | 6 | 动态 `import("echarts")` 避免 SSR 报错 |
| 后端语言 | Python | 3.11+ | |
| 后端框架 | FastAPI | 0.115+ | |
| 数据库 | MySQL | 8.0 | |
| ORM | SQLAlchemy | 2.0 async | |
| 任务调度 | APScheduler | 3.10 | 嵌入 FastAPI lifespan，可迁移 Celery |
| AI 层 | MiniMax ChatCompletion V2 | — | 工厂模式，`.env` 一行切换模型 |
| 搜索层 | DuckDuckGo（默认） | — | 工厂模式，可扩展其他搜索引擎 |
| 容器化 | Docker Compose | — | |

---

## 2. 系统架构

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Docker Compose                               │
│                                                                      │
│  ┌──────────────┐   fetch    ┌──────────────────────────────┐       │
│  │  Next.js     │ ─────────► │         FastAPI               │       │
│  │  :3000       │ ◄───JSON── │  /api/v1/trends               │       │
│  └──────────────┘            │  /api/v1/ai                   │       │
│                               │  /api/v1/signals              │       │
│                               │  /api/v1/alerts               │       │
│                               │  :8000                        │       │
│                               └──────────┬───────────────────┘       │
│                                          │                            │
│         ┌────────────────────────────────┼───────────────┐           │
│         ▼                    ▼           ▼               ▼           │
│  ┌────────────────┐  ┌────────────┐  ┌──────────┐  ┌─────────┐     │
│  │ Collector Layer │  │  AI Layer   │  │ Search   │  │  MySQL  │     │
│  │ (asyncio)       │  │ (LLMFactory)│  │ Layer    │  │  :3306  │     │
│  │                │  │            │  │(Factory) │  └─────────┘     │
│  │ Weibo          │  │ MiniMax    │  │ DDG      │                  │
│  │ Google         │  │ (可扩展)   │  │ (可扩展)  │                  │
│  │ TikTok         │  └────────────┘  └──────────┘                  │
│  │ [可插拔]       │                                                 │
│  └────────────────┘                                                 │
│       ▲  asyncio.gather 并发采集                                    │
│  ┌──────────────────┐                                               │
│  │   APScheduler    │  分平台独立 cron                              │
│  │                  │  简报: 每天 08:00                              │
│  └──────────────────┘                                               │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. AI 智能管线（核心数据流）

采集完成后，数据经过三级 AI 管线处理：

```
┌─ Stage 1: 采集 ──────────────────────────────────────────────────┐
│  asyncio.gather 并发采集 → Replace-by-hour 去重 → 入库            │
└──────────────────────────────────────────────────────────────────┘
                                ↓
┌─ Stage 2: AI 过滤 + 重要性评分（一次 LLM 调用）────────────────┐
│  输入: 30条关键词(batch) + 用户画像                              │
│  LLM 输出: [{"i":1,"s":85,"r":"理由"}, ...]                     │
│  未出现 → irrelevant, score=0                                    │
│  Fallback: JSON → code fence → regex → 纯索引退化               │
│  写回: Trend.relevance_score + Trend.relevance_label             │
└──────────────────────────────────────────────────────────────────┘
                                ↓
┌─ Stage 3: 信号检测（纯算法）─────────────────────────────────────┐
│  rank_jump:  排名跃升 ≥20 位（6h 回看）                          │
│  new_entry:  首次进入 Top 50（24h 内未出现过）                    │
│  heat_surge: 热度 ≥ 2× 上次采集                                  │
│  → 去重（1h 窗口）→ 入库 SignalLog                               │
└──────────────────────────────────────────────────────────────────┘
                                ↓
┌─ Stage 4: 深度分析（Top N）──────────────────────────────────────┐
│  触发: 自动(score最高N条) + 手动(用户点击)                        │
│  24h 去重: 同关键词不重复分析                                     │
│  流程:                                                            │
│    1. SearchFactory.create().search(keyword) → Top 5 结果         │
│    2. 搜索结果 + 热搜元数据 → LLM 深度分析                       │
│    3. 输出结构化报告: 背景/机会/风险/行动/来源URLs                │
│    4. 存入 AIInsight (deep_analysis + source_urls)                │
└──────────────────────────────────────────────────────────────────┘
                                ↓
┌─ 每日简报（独立定时任务 08:00）──────────────────────────────────┐
│  信号驱动: 优先使用近 24h 信号（限 10 条）                        │
│  相关性过滤: 仅使用 relevance_label="relevant" 的信号和热词       │
│  Fallback: 无信号时使用 Top 20 热词                               │
│  → LLM 生成简报 → 入库 DailyBrief → 邮件推送                    │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. 采集层设计

### 4.1 插件化架构

所有数据源实现 `BaseCollector` 抽象接口，通过 `CollectorRegistry` 统一管理。

```python
# 接口约定（collectors/base.py）
class BaseCollector(ABC):
    platform: str          # 平台唯一标识，如 "weibo"

    @abstractmethod
    async def collect(self) -> list[dict]:
        """返回标准字段列表：platform, keyword, rank, heat_score, url, collected_at"""

    @staticmethod
    def _now() -> datetime: ...
```

### 4.2 新增平台步骤（仅需 2 个文件）

```
backend/app/collectors/
├── {platform}.py       # 1. 实现 BaseCollector，platform = "{platform}"
├── {platform}_mock.py  # 2. 实现 Mock 版（固定数据，用于 CI 测试）
└── __init__.py         # 3. 注册：registry.register({Platform}Collector)
```

前端同步在 `frontend/lib/platform-config.ts` 添加一条展示配置（名称/颜色）。

### 4.3 已实现平台

| 平台 | 数据源 | 热度字段 | 典型量级 |
|------|--------|----------|---------|
| `weibo` | `weibo.com/ajax/side/hotSearch` JSON | `num`（热搜指数） | 万级 |
| `google` | Google Trends 每日 RSS XML | `approx_traffic`（搜索量） | 百万级 |
| `tiktok` | TikTok Creative Center API JSON | `video_views`（播放量） | 十亿级 |

### 4.4 并发采集 + Replace-by-hour

```python
# services/collector.py
results = await asyncio.gather(*(_collect_one(slug) for slug in platforms))
```

- 所有平台并发采集，总耗时 = 最慢平台耗时
- 同平台同小时内重复采集会替换旧数据（防止手动+定时重复）
- 分平台独立 cron 调度（微博 2h、TikTok 6h、其他用全局默认）

---

## 5. 搜索层设计

### 5.1 工厂模式

与 AI 层和采集层一致，搜索层使用工厂模式，支持扩展：

```
app/search/
├── base.py          # BaseSearchProvider (abstract)
├── factory.py       # SearchFactory
└── duckduckgo.py    # DuckDuckGoProvider (默认)
```

### 5.2 接口定义

```python
@dataclass
class SearchResult:
    title: str       # 搜索结果标题
    snippet: str     # 摘要
    url: str         # 来源 URL

class BaseSearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """搜索并返回结果列表"""
```

### 5.3 扩展方式

新增搜索引擎只需：
1. `app/search/{engine}.py` — 实现 `BaseSearchProvider`
2. 在 `SearchFactory` 注册
3. `.env` 中设置 `SEARCH_PROVIDER={engine}`

---

## 6. AI 层设计

### 6.1 工厂模式

```python
# LLMFactory 统一创建 Provider
LLMFactory._PROVIDERS = {
    "minimax": "app.ai.minimax_provider.MiniMaxProvider",
}
# .env 中 LLM_PROVIDER=minimax 即可切换
```

### 6.2 Provider 接口

```python
class BaseLLMProvider(ABC):
    async def chat(self, messages: list[ChatMessage], **kwargs) -> ChatResponse
    async def analyze(self, keyword: str, context: str = "", ...) -> AnalyzeResponse
```

### 6.3 AI 调用场景

| 场景 | 函数 | 输入 | 输出 |
|------|------|------|------|
| 过滤+打分 | `score_relevance()` | 关键词列表 + 用户画像 | `{keyword: {score, label, reason}}` |
| 信号摘要 | `auto_analyze_signals()` | 信号列表 | SignalLog.ai_summary (500字) |
| 深度分析 | `deep_analyze()` | 关键词 + 搜索结果 | 结构化报告 (背景/机会/风险/行动) |
| 每日简报 | `generate_daily_brief()` | 信号 + Top 热词 | DailyBrief.content |
| 单词分析 | `analyze_keyword()` | 单个关键词 | business_insight + sentiment + related |

---

## 7. 收敛评分算法

### 7.1 设计原则

各平台热度量纲差异巨大，不可直接横向比较，评分**只在同平台内部有意义**。

### 7.2 计算公式

```python
def compute_convergence_score(
    heat_score: float | None,
    rank: int | None,
    age_hours: float,
    platform_max_heat: float,   # 同平台同批次最高热度
) -> float:
    # 热度分：该词相对于同平台最高热度的百分比
    heat_component = min(100.0, heat_score / platform_max_heat * 100)
        if heat_score and platform_max_heat > 0 else 0.0

    # 排名分：线性，rank=0 → 100分，rank=49 → 0分
    rank_component = max(0.0, (50 - (rank + 1)) / 50 * 100)
        if rank is not None else 0.0

    raw = heat_component * 0.5 + rank_component * 0.5

    # 时间衰减：半衰期 12 小时
    decay = exp(-age_hours * ln(2) / 12)

    return round(min(100.0, max(0.0, raw * decay)), 2)
```

### 7.3 关键词动量（Velocity）

基于 3 个时间段（T0/T1/T2）计算：
- **velocity**: 当前周期热度变化率（%）
- **acceleration**: 变化率的变化（加速/减速）

---

## 8. 信号检测层

### 8.1 信号类型

| 类型 | 检测逻辑 | 阈值 |
|------|---------|------|
| `rank_jump` | 排名较 6h 内最差排名提升 | ≥ 20 位 |
| `new_entry` | 24h 内首次进入 Top 50 | — |
| `heat_surge` | 热度对比上次采集 | ≥ 2.0× |

### 8.2 去重

同平台同关键词同类型信号在 1 小时内不重复记录。

### 8.3 自动分析

检测到信号后，按 `value`（跃升幅度/飙升倍数）降序排列，取 Top N（可配置，默认 3）自动调用 AI 生成 500 字摘要，存入 `SignalLog.ai_summary`。

---

## 9. 前端架构

### 9.1 目录结构

```
frontend/
├── app/                         # App Router
│   ├── layout.tsx               # 根布局（侧边栏）
│   ├── page.tsx                 # / 仪表盘（分平台热词排行）
│   ├── trends/page.tsx          # /trends 趋势列表（分页 + 智能过滤）
│   ├── ai/page.tsx              # /ai AI 分析
│   ├── alerts/page.tsx          # /alerts 告警规则
│   └── settings/page.tsx        # /settings 设置
├── components/
│   ├── AppSidebar.tsx
│   ├── TopKeywordsChart.tsx     # ECharts 横向柱状图（单平台）
│   └── ui/                      # shadcn 基础组件
├── lib/
│   ├── api.ts                   # 所有后端请求
│   ├── platform-config.ts       # 平台展示配置（名称/颜色）← 扩展入口
│   └── utils.ts
└── hooks/
    └── use-mobile.ts
```

### 9.2 平台展示配置（扩展入口）

```typescript
// lib/platform-config.ts
export const PLATFORM_CONFIG: Record<string, PlatformMeta> = {
  weibo:  { displayName: "微博热搜",    color: "#e2231a" },
  google: { displayName: "Google 趋势", color: "#4285f4" },
  tiktok: { displayName: "TikTok",      color: "#010101" },
  // 新增平台在此添加一行 ↑
}
```

---

## 10. 后端 API 路由总览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/api/v1/trends` | 分页趋势列表（支持 `platform`、`relevant_only` 过滤） |
| GET | `/api/v1/trends/top` | 全局 Top N（按收敛评分） |
| GET | `/api/v1/trends/top-by-platform` | 各平台独立 Top N（仪表盘使用） |
| GET | `/api/v1/trends/heatmap` | 24h 热力图数据 |
| GET | `/api/v1/trends/velocity` | 关键词动量（速度+加速度） |
| GET | `/api/v1/trends/platforms` | 已注册平台列表 |
| GET | `/api/v1/trends/count` | 趋势记录总数 |
| DELETE | `/api/v1/trends/all` | 清空趋势数据 |
| POST | `/api/v1/collector/collect` | 手动触发采集 |
| POST | `/api/v1/ai/analyze` | AI 单词分析 |
| POST | `/api/v1/ai/deep-analyze` | 深度分析（搜索+AI） |
| GET | `/api/v1/ai/deep-analyze/{keyword}` | 获取深度分析结果 |
| POST | `/api/v1/ai/brief` | 手动触发每日简报生成 |
| GET | `/api/v1/ai/brief/latest` | 获取最新简报 |
| GET | `/api/v1/signals/recent` | 近期信号列表 |
| POST | `/api/v1/signals/detect` | 手动触发信号检测 |
| POST | `/api/v1/alerts/keywords` | 创建关键词监控规则 |
| GET | `/api/v1/alerts/keywords` | 列出所有监控规则 |
| GET | `/api/v1/scheduler/status` | 调度器任务状态 |

---

## 11. 关键设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 评分是否跨平台合并 | ❌ 不合并，各平台独立评分 | 热度量纲差异太大；关键词格式不同无法匹配 |
| 跨平台展示方式 | 分平台独立卡片 | 不同平台语言不同、量纲不同，混合排行造成语言混杂 |
| 采集并发 | `asyncio.gather` | 从串行 O(n×t) 降为并行 O(max_t) |
| 任务调度 | APScheduler 嵌入 FastAPI | MVP 任务量小，无需 Celery+Redis |
| AI Provider | 工厂模式，`.env` 切换 | 国内模型迭代快，切换成本为零 |
| 搜索 Provider | 工厂模式，`.env` 切换 | 搜索引擎可能被限流，需要切换备选 |
| AI 过滤+打分合一 | 一次 LLM 调用完成 | 减少 API 调用次数和延迟 |
| 深度分析去重 | 24h 窗口 | 避免浪费 API 调用，同一事件短期内不会剧变 |
| 组件库 | shadcn + @base-ui/react | 注意：非 Radix UI，改组件时查 Base UI 文档 |

---

## 12. 项目目录结构

```
trendTracker/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── collectors/
│   │   │   ├── base.py          # BaseCollector 抽象类
│   │   │   ├── registry.py      # CollectorRegistry
│   │   │   ├── weibo.py         # 微博（真实）
│   │   │   ├── weibo_mock.py
│   │   │   ├── google.py        # Google Trends RSS
│   │   │   ├── google_mock.py
│   │   │   ├── tiktok.py        # TikTok Creative Center
│   │   │   └── tiktok_mock.py
│   │   ├── ai/
│   │   │   ├── base.py          # BaseLLMProvider
│   │   │   ├── factory.py       # LLMFactory
│   │   │   └── minimax_provider.py
│   │   ├── search/              # 搜索层（新增）
│   │   │   ├── base.py          # BaseSearchProvider
│   │   │   ├── factory.py       # SearchFactory
│   │   │   └── duckduckgo.py    # DuckDuckGo 默认实现
│   │   ├── models/              # SQLAlchemy 模型
│   │   ├── schemas/             # Pydantic 请求/响应
│   │   ├── routers/             # FastAPI 路由
│   │   └── services/            # 业务逻辑
│   │       ├── collector.py     # 采集编排 + AI 管线触发
│   │       ├── trends.py        # 趋势查询 + 评分
│   │       ├── relevance.py     # AI 过滤 + 重要性评分
│   │       ├── signals.py       # 信号检测 + 自动分析
│   │       ├── deep_analysis.py # 深度分析（搜索+AI）（新增）
│   │       ├── brief.py         # 每日简报
│   │       ├── ai.py            # 单词 AI 分析
│   │       ├── alerts.py        # 告警检查
│   │       └── scheduler.py     # 定时任务调度
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── app/                     # Next.js App Router
│   ├── components/
│   ├── lib/
│   │   ├── api.ts
│   │   └── platform-config.ts   # ← 平台扩展配置入口
│   └── package.json
├── docs/
├── docker-compose.yml
└── .env.example
```
