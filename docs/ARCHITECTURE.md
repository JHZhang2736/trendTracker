# 系统架构图
# TrendTracker — System Architecture

**最后更新**: 2026-03-22

---

## 1. 整体系统架构

```mermaid
graph TB
    subgraph Client["浏览器"]
        UI[Next.js 前端<br/>Port 3000]
    end

    subgraph Backend["FastAPI 后端 Port 8000"]
        direction TB
        Router[Routers 路由层<br/>trends / ai / signals / collector / alerts]
        Service[Services 业务逻辑层]
        Scheduler[APScheduler<br/>分平台独立 cron]

        Router --> Service
        Scheduler --> Service
    end

    subgraph CollectorLayer["采集层（插件化）"]
        direction LR
        GC[GoogleCollector<br/>RSS]
        TC[TikTokCollector<br/>Creative Center API]
        WC[WeiboCollector<br/>JSON API]
        EXT[[ + 可扩展 ]]
    end

    subgraph AILayer["AI层（工厂模式）"]
        direction LR
        LLMFactory[LLMFactory]
        MM[MiniMaxProvider]
        LLMFactory --> MM
    end

    subgraph SearchLayer["搜索层（工厂模式）"]
        direction LR
        SearchFactory[SearchFactory]
        DDG[DuckDuckGoProvider]
        SearchFactory --> DDG
    end

    subgraph DataSources["外部数据源"]
        direction LR
        Google[Google Trends]
        TikTok[TikTok]
        Weibo[微博]
    end

    subgraph Storage["存储层"]
        MySQL[(MySQL 8.0<br/>Port 3306)]
    end

    subgraph Notify["通知"]
        Email[邮件 SMTP]
    end

    UI -->|REST API / JSON| Router
    Service --> CollectorLayer
    Service --> AILayer
    Service --> SearchLayer
    Service --> MySQL
    Service --> Email

    GC -->|采集| Google
    TC -->|采集| TikTok
    WC -->|采集| Weibo
```

---

## 2. AI 智能管线数据流

```mermaid
flowchart TD
    subgraph Collect["Stage 1: 采集"]
        A[APScheduler 触发<br/>分平台独立 cron] --> B[CollectorRegistry]
        B --> C1[Weibo]
        B --> C2[Google]
        B --> C3[TikTok]
        C1 & C2 & C3 --> D[Replace-by-hour 去重]
        D --> E[(trends 表)]
    end

    subgraph Filter["Stage 2: AI 过滤 + 重要性评分"]
        E --> F[批量取未评分关键词<br/>max 30/batch]
        F --> G[LLM 过滤+打分<br/>返回 JSON: i/s/r]
        G --> H[写回 relevance_score<br/>relevance_label<br/>relevance_reason]
    end

    subgraph Signal["Stage 3: 信号检测"]
        H --> I[rank_jump 排名跃升]
        H --> J[new_entry 新上榜]
        H --> K[heat_surge 热度飙升]
        I & J & K --> L[去重 1h 窗口]
        L --> M[(signal_logs 表)]
    end

    subgraph DeepAnalysis["Stage 4: 深度分析"]
        M --> N[取 score 最高 Top N]
        N --> O{24h 内已分析?}
        O -->|是| P[跳过]
        O -->|否| Q[SearchFactory.search<br/>获取 Top 5 搜索结果]
        Q --> R[LLM 深度分析<br/>背景/机会/风险/行动]
        R --> S[(ai_insights 表<br/>deep_analysis 字段)]
    end

    subgraph Brief["每日简报 (08:00)"]
        M --> T[取近24h信号]
        T --> U[相关性过滤]
        U --> V[LLM 生成简报]
        V --> W[(daily_briefs 表)]
        W --> X[邮件推送]
    end
```

---

## 3. 插件化采集层

```mermaid
classDiagram
    class BaseCollector {
        <<abstract>>
        +platform: str
        +collect() list~dict~
        +_now() datetime
    }

    class CollectorRegistry {
        -_collectors: dict
        +register(collector)
        +get(slug) type
        +list_platforms() list
    }

    class WeiboCollector {
        +platform = "weibo"
        +collect()
    }

    class GoogleCollector {
        +platform = "google"
        +collect()
    }

    class TikTokCollector {
        +platform = "tiktok"
        +collect()
    }

    BaseCollector <|-- WeiboCollector
    BaseCollector <|-- GoogleCollector
    BaseCollector <|-- TikTokCollector
    CollectorRegistry o-- BaseCollector
```

---

## 4. AI 多模型工厂

```mermaid
classDiagram
    class BaseLLMProvider {
        <<abstract>>
        +chat(messages, **kwargs) ChatResponse
        +analyze(keyword, context, insight_type) AnalyzeResponse
    }

    class LLMFactory {
        -_PROVIDERS: dict
        +create(provider_name) BaseLLMProvider
    }

    class MiniMaxProvider {
        +model: str
        +api_key: str
        +chat()
        +analyze()
    }

    class ChatMessage {
        +role: str
        +content: str
    }

    class ChatResponse {
        +content: str
        +model: str
        +usage: dict
    }

    class AnalyzeResponse {
        +insight_type: str
        +content: str
        +model: str
        +extra: dict
    }

    BaseLLMProvider <|-- MiniMaxProvider
    LLMFactory ..> BaseLLMProvider : creates
    BaseLLMProvider ..> ChatMessage : receives
    BaseLLMProvider ..> ChatResponse : returns
    BaseLLMProvider ..> AnalyzeResponse : returns
```

---

## 5. 搜索层工厂

```mermaid
classDiagram
    class BaseSearchProvider {
        <<abstract>>
        +search(query, max_results) list~SearchResult~
    }

    class SearchFactory {
        -_PROVIDERS: dict
        +create(provider_name) BaseSearchProvider
    }

    class DuckDuckGoProvider {
        +search(query, max_results)
    }

    class SearchResult {
        +title: str
        +snippet: str
        +url: str
    }

    BaseSearchProvider <|-- DuckDuckGoProvider
    SearchFactory ..> BaseSearchProvider : creates
    BaseSearchProvider ..> SearchResult : returns
```

---

## 6. Docker Compose 服务关系

```mermaid
graph LR
    subgraph compose["Docker Compose"]
        FE[frontend<br/>Next.js<br/>:3000]
        BE[backend<br/>FastAPI<br/>:8000]
        DB[(mysql<br/>MySQL 8.0<br/>:3306)]
    end

    Browser[浏览器] -->|http://localhost:3000| FE
    FE -->|http://backend:8000| BE
    BE -->|tcp://mysql:3306| DB

    BE -.->|定时采集| Internet[外部数据源]
    BE -.->|AI API| LLMAPI[MiniMax API]
    BE -.->|搜索| SearchAPI[DuckDuckGo]
    BE -.->|SMTP| EmailSrv[邮件服务]
```

---

## 7. 数据库 ER 图

```mermaid
erDiagram
    platforms {
        int id PK
        varchar name
        varchar slug UK
    }

    trends {
        bigint id PK
        int platform_id FK
        varchar platform
        varchar keyword
        smallint rank
        float heat_score
        varchar url
        datetime collected_at
        float relevance_score
        varchar relevance_label
        varchar relevance_reason
    }

    signal_logs {
        bigint id PK
        varchar signal_type
        varchar platform
        varchar keyword
        varchar description
        float value
        varchar ai_summary
        datetime detected_at
    }

    ai_insights {
        bigint id PK
        varchar keyword
        bigint trend_id FK
        varchar insight_type
        text content
        varchar model
        text search_context
        text deep_analysis
        text source_urls
        varchar analysis_type
        datetime created_at
    }

    daily_briefs {
        bigint id PK
        date date UK
        text content
        varchar model
        datetime created_at
    }

    keyword_alerts {
        bigint id PK
        varchar keyword
        float threshold
        varchar email
        tinyint is_active
    }

    alert_logs {
        bigint id PK
        bigint alert_id FK
        varchar keyword
        varchar platform
        float heat_score
        tinyint notified
    }

    platforms ||--o{ trends : "has"
    trends }o--o| ai_insights : "trend_id"
    keyword_alerts ||--o{ alert_logs : "triggers"
```
