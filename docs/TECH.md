# 技术文档
# TrendTracker — 架构设计与实现说明

**文档版本**: v0.2
**最后更新**: 2026-03-19

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
| 容器化 | Docker Compose | — | |

---

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Docker Compose                          │
│                                                             │
│  ┌──────────────┐   fetch    ┌─────────────────────────┐   │
│  │  Next.js     │ ─────────► │       FastAPI            │   │
│  │  :3000       │ ◄───JSON── │  /api/v1/trends          │   │
│  └──────────────┘            │  /api/v1/ai              │   │
│                               │  /api/v1/alerts          │   │
│                               │  :8000                   │   │
│                               └──────────┬──────────────┘   │
│                                          │                   │
│              ┌───────────────────────────┼──────────┐       │
│              ▼                           ▼          ▼       │
│  ┌──────────────────┐   ┌────────────────────┐  ┌───────┐  │
│  │  Collector Layer  │   │   AI Layer          │  │ MySQL │  │
│  │  (asyncio.gather) │   │  (LLMFactory)       │  │ :3306 │  │
│  │                  │   │                    │  └───────┘  │
│  │ WeiboCollector   │   │ MiniMaxProvider    │             │
│  │ GoogleCollector  │   │ (可扩展其他Provider)│             │
│  │ TikTokCollector  │   └────────────────────┘             │
│  │ [可插拔]         │                                       │
│  └──────────────────┘                                       │
│         ▲  asyncio.gather 并发采集                          │
│  ┌──────────────────┐                                       │
│  │   APScheduler    │  collect: 每1小时                     │
│  │                  │  brief:   每天 08:00                  │
│  └──────────────────┘                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 采集层设计

### 3.1 插件化架构

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

### 3.2 新增平台步骤（仅需 2 个文件）

```
backend/app/collectors/
├── {platform}.py       # 1. 实现 BaseCollector，platform = "{platform}"
├── {platform}_mock.py  # 2. 实现 Mock 版（固定数据，用于 CI 测试）
└── __init__.py         # 3. 注册：registry.register({Platform}Collector)
```

前端同步在 `frontend/lib/platform-config.ts` 添加一条展示配置（名称/颜色）。

### 3.3 已实现平台

| 平台 | 数据源 | 热度字段 | 典型量级 |
|------|--------|----------|---------|
| `weibo` | `weibo.com/ajax/side/hotSearch` JSON | `num`（热搜指数） | 万级 |
| `google` | Google Trends 每日 RSS XML | `approx_traffic`（搜索量） | 百万级 |
| `tiktok` | TikTok Creative Center API JSON | `video_views`（播放量） | 十亿级 |

### 3.4 并发采集

```python
# services/collector.py
results = await asyncio.gather(*(_collect_one(slug) for slug in platforms))
```

所有平台并发采集，总耗时 = 最慢平台耗时（而非各平台之和）。

---

## 4. 收敛评分算法

### 4.1 设计原则

各平台热度量纲差异巨大，不可直接横向比较，评分**只在同平台内部有意义**。

### 4.2 计算公式

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

**关键变化（v0.2）**：
- `max_heat` 改为**同平台内取**，不再全局取（消除 TikTok 十亿级数值压制其他平台）
- 移除 `platform_component`（跨平台同词合并几乎不发生）

---

## 5. 前端架构

### 5.1 目录结构（实际）

```
frontend/
├── app/                         # App Router
│   ├── layout.tsx               # 根布局（侧边栏）
│   ├── page.tsx                 # / 仪表盘（分平台热词排行）
│   ├── trends/page.tsx          # /trends 趋势列表（分页）
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

### 5.2 平台展示配置（扩展入口）

```typescript
// lib/platform-config.ts
export const PLATFORM_CONFIG: Record<string, PlatformMeta> = {
  weibo:  { displayName: "微博热搜",    color: "#e2231a" },
  google: { displayName: "Google 趋势", color: "#4285f4" },
  tiktok: { displayName: "TikTok",      color: "#010101" },
  // 新增平台在此添加一行 ↑
}
```

前端所有组件通过此配置获取展示名和颜色，不硬编码在组件里。

### 5.3 数据流

```
page.tsx
  └─ useEffect → api.trends.topByPlatform()
       └─ lib/api.ts → fetch(NEXT_PUBLIC_API_URL + "/api/v1/trends/top-by-platform")
            └─ FastAPI → get_top_trends_by_platform(db)
                 └─ 各平台独立计算收敛评分，返回 {platform: {items: [...]}}
```

---

## 6. 后端 API 路由总览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/api/v1/trends` | 分页趋势列表（含收敛评分） |
| GET | `/api/v1/trends/top` | 全局 Top N（按收敛评分，已废弃跨平台合并） |
| GET | `/api/v1/trends/top-by-platform` | **各平台独立 Top N**（主要使用） |
| GET | `/api/v1/trends/platforms` | 已注册平台列表 |
| POST | `/api/v1/collector/run` | 手动触发采集 |
| POST | `/api/v1/ai/analyze` | AI 单词分析 |
| POST | `/api/v1/ai/brief` | 手动触发每日简报生成 |
| GET | `/api/v1/ai/brief/latest` | 获取最新简报 |
| POST | `/api/v1/alerts/keywords` | 创建关键词监控规则 |
| GET | `/api/v1/alerts/keywords` | 列出所有监控规则 |
| GET | `/api/v1/scheduler/status` | 调度器任务状态 |

---

## 7. 关键设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 评分是否跨平台合并 | ❌ 不合并，各平台独立评分 | 热度量纲差异太大；关键词格式不同无法匹配 |
| 跨平台展示方式 | 分平台独立柱状图 | 保留各平台语义，用户可自行判断跨平台共振 |
| 采集并发 | `asyncio.gather` | 从串行 O(n×t) 降为并行 O(max_t) |
| 任务调度 | APScheduler 嵌入 FastAPI | MVP 任务量小，无需 Celery+Redis；代码解耦便于迁移 |
| AI Provider | 工厂模式，`.env` 切换 | 国内模型迭代快，切换成本为零 |
| 组件库 | shadcn + @base-ui/react | 注意：非 Radix UI，改组件时查 Base UI 文档 |

---

## 8. 项目目录结构（实际）

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
│   │   ├── models/              # SQLAlchemy 模型
│   │   ├── schemas/             # Pydantic 请求/响应
│   │   ├── routers/             # FastAPI 路由
│   │   └── services/            # 业务逻辑
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
