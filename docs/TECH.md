# 技术分析文档
# TrendTracker — MVP 技术选型与架构设计

**文档版本**: v0.1
**创建日期**: 2026-03-19
**阶段**: MVP

---

## 1. 技术栈总览

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| 前端框架 | React + Next.js | App Router，支持 SSR/CSR 混合 |
| 前端样式 | Tailwind CSS | 原子化 CSS |
| 前端组件库 | shadcn/ui | 基于 Radix UI，风格统一 |
| 前端图表 | ECharts（echarts-for-react） | 热力图、折线图、柱状图全覆盖 |
| 后端语言 | Python 3.11+ | |
| 后端框架 | FastAPI | 异步、高性能，自动生成 API 文档 |
| 数据库 | MySQL 8.0 | 趋势数据持久化存储 |
| ORM | SQLAlchemy 2.0 + Alembic | 数据模型管理与迁移 |
| 任务调度 | APScheduler | 嵌入 FastAPI，定时触发采集任务 |
| AI 模型 | 多模型抽象层，初期接入 MiniMax API | 支持后续切换 DeepSeek / 通义千问等 |
| 容器化 | Docker + Docker Compose | 一键启动所有服务 |

---

## 2. 系统架构

```
┌──────────────────────────────────────────────────────────────┐
│                        Docker Compose                         │
│                                                              │
│  ┌─────────────────┐         ┌──────────────────────────┐   │
│  │   Next.js        │ ──API──►│        FastAPI            │   │
│  │   前端界面        │◄──JSON─│   /api/trends             │   │
│  │  (Port 3000)     │         │   /api/ai                 │   │
│  └─────────────────┘         │   /api/alerts             │   │
│                               │   (Port 8000)             │   │
│                               └────────────┬─────────────┘   │
│                                            │                  │
│              ┌─────────────────────────────┼────────────┐    │
│              │                             │            │    │
│              ▼                             ▼            ▼    │
│  ┌──────────────────┐  ┌─────────────────────┐  ┌──────────┐│
│  │  Collector Layer  │  │    AI Adapter Layer  │  │  MySQL   ││
│  │  (插件化采集层)   │  │   (多模型适配层)     │  │ (3306)   ││
│  │                  │  │                     │  └──────────┘│
│  │ • GoogleCollector│  │ • MiniMaxAdapter    │              │
│  │ • TikTokCollector│  │ • DeepSeekAdapter   │              │
│  │ • WeiboCollector │  │ • QwenAdapter       │              │
│  │ • BaiduCollector │  │ (统一 LLMProvider   │              │
│  │ • [可插拔扩展]   │  │  接口)              │              │
│  └──────────────────┘  └─────────────────────┘              │
│              ▲                                               │
│              │ 定时触发                                      │
│  ┌──────────────────┐                                        │
│  │   APScheduler    │                                        │
│  │  (嵌入FastAPI)   │                                        │
│  └──────────────────┘                                        │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. 插件化采集层设计（核心）

所有数据源实现统一的 `BaseCollector` 抽象接口，新增数据源只需实现接口并注册，无需修改核心逻辑。

### 3.1 接口定义

```python
# collectors/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

@dataclass
class TrendItem:
    keyword: str          # 关键词
    platform: str         # 来源平台
    score: float          # 热度分数（归一化到0-100）
    rank: int | None      # 排名（如有）
    collected_at: datetime
    raw_data: dict        # 原始数据，保留备查

class BaseCollector(ABC):
    name: str             # 平台标识，如 "google", "weibo"
    enabled: bool = True  # 可通过配置动态禁用

    @abstractmethod
    async def fetch(self) -> List[TrendItem]:
        """采集数据，返回标准化结果"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """检查数据源是否可用"""
        pass
```

### 3.2 Collector 注册中心

```python
# collectors/registry.py
class CollectorRegistry:
    _collectors: dict[str, BaseCollector] = {}

    @classmethod
    def register(cls, collector: BaseCollector):
        cls._collectors[collector.name] = collector

    @classmethod
    def get_enabled(cls) -> list[BaseCollector]:
        return [c for c in cls._collectors.values() if c.enabled]
```

### 3.3 各数据源实现方案

| 数据源 | 实现方案 | 依赖库 | 稳定性 |
|--------|----------|--------|--------|
| Google Trends | `pytrends`（archived但可用） | pytrends | ⭐⭐⭐ |
| TikTok | `davidteather/TikTok-Api`（6190⭐） | playwright | ⭐⭐⭐⭐ |
| 微博热搜 | 自写轻量爬虫（`s.weibo.com/top/summary`，纯HTML） | httpx + bs4 | ⭐⭐⭐⭐ |
| 百度指数 | `baidu-index-spider`（需账号Cookie） | requests | ⭐⭐（Cookie失效风险） |
| 阿里指数 | 暂跳过，预留插槽 | — | — |

---

## 4. AI 多模型抽象层设计

### 4.1 接口定义

```python
# ai/base.py
from abc import ABC, abstractmethod

class BaseLLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: list[dict], **kwargs) -> str:
        pass

    @abstractmethod
    async def analyze_trend(self, keyword: str, context: dict) -> TrendAnalysis:
        """分析单个趋势的商业价值"""
        pass
```

### 4.2 Provider 工厂

```python
# ai/factory.py
class LLMFactory:
    @staticmethod
    def create(provider: str) -> BaseLLMProvider:
        match provider:
            case "minimax": return MiniMaxProvider()
            case "deepseek": return DeepSeekProvider()
            case "qwen":     return QwenProvider()
            case _: raise ValueError(f"Unknown provider: {provider}")
```

通过 `.env` 配置 `LLM_PROVIDER=minimax` 即可切换模型，无需改代码。

---

## 5. 项目目录结构

```
trendTracker/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI 入口
│   │   ├── config.py               # 配置加载
│   │   ├── database.py             # MySQL 连接
│   │   ├── scheduler.py            # APScheduler 初始化
│   │   ├── collectors/
│   │   │   ├── base.py             # BaseCollector 抽象类
│   │   │   ├── registry.py         # 注册中心
│   │   │   ├── google.py           # Google Trends
│   │   │   ├── tiktok.py           # TikTok
│   │   │   ├── weibo.py            # 微博热搜
│   │   │   └── baidu.py            # 百度指数
│   │   ├── ai/
│   │   │   ├── base.py             # BaseLLMProvider
│   │   │   ├── factory.py          # Provider 工厂
│   │   │   ├── minimax.py          # MiniMax 实现
│   │   │   ├── deepseek.py         # DeepSeek 实现（预留）
│   │   │   └── prompts.py          # Prompt 模板管理
│   │   ├── models/                 # SQLAlchemy 数据模型
│   │   ├── schemas/                # Pydantic 请求/响应模型
│   │   ├── routers/                # FastAPI 路由
│   │   │   ├── trends.py
│   │   │   ├── ai.py
│   │   │   └── alerts.py
│   │   └── services/               # 业务逻辑层
│   ├── alembic/                    # 数据库迁移
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── app/                    # Next.js App Router
│   │   ├── components/
│   │   │   ├── ui/                 # shadcn 组件
│   │   │   ├── charts/             # ECharts 封装组件
│   │   │   └── trends/             # 业务组件
│   │   ├── lib/                    # API 调用封装
│   │   └── types/
│   ├── package.json
│   └── Dockerfile
│
├── docs/
│   ├── PRD.md
│   ├── TECH.md
│   └── conversation_history.md
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 6. Docker Compose 服务编排

```yaml
# docker-compose.yml（结构示意）
services:
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [backend]

  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [mysql]

  mysql:
    image: mysql:8.0
    ports: ["3306:3306"]
    volumes: [mysql_data:/var/lib/mysql]
    environment:
      MYSQL_DATABASE: trendtracker

volumes:
  mysql_data:
```

---

## 7. 关键设计决策记录

| 决策 | 选择 | 放弃的选项 | 原因 |
|------|------|-----------|------|
| 任务调度 | APScheduler（嵌入FastAPI） | Celery + Redis | MVP阶段任务量小，减少服务数量；代码已解耦便于后续迁移 |
| 数据源架构 | 插件化 BaseCollector | 硬编码各平台 | 数据源不稳定，需要随时禁用/替换；未来扩展无需改核心逻辑 |
| AI层架构 | Provider 工厂模式 | 直接调用单一API | 国内模型迭代快，切换成本应为零 |
| 阿里指数 | 暂跳过 | 爬虫/付费API | 无可用开源方案，付费方案与MVP免费原则冲突 |
| 图表库 | ECharts | Recharts | 热力图等复杂图表原生支持，中文文档完善 |

---

## 8. 待确认的开放问题

| 问题 | 优先级 |
|------|--------|
| 百度指数 Cookie 获取与轮换方案 | 中 |
| TikTok-Api 的 Playwright 在 Docker 内的配置 | 高 |
| MiniMax API 的 rate limit 与采集频率匹配 | 中 |
| MySQL 趋势数据的索引设计（时间序列查询优化） | 低（开发时再定） |

---

*技术选型完成，下一步：开始开发*
