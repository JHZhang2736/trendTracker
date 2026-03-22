# API 设计文档
# TrendTracker — REST API Specification

**文档版本**: v0.2
**最后更新**: 2026-03-22
**Base URL**: `http://localhost:8000/api/v1`
**格式**: JSON
**字符集**: UTF-8

---

## 1. 通用规范

### 1.1 HTTP 状态码

| 状态码 | 含义 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

### 1.2 分页参数（列表接口通用）

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | 1 | 页码 |
| `page_size` | int | 20 | 每页条数，最大100 |

### 1.3 平台标识

| 值 | 平台 |
|----|------|
| `weibo` | 微博热搜 |
| `google` | Google Trends |
| `tiktok` | TikTok |

---

## 2. 趋势数据接口（Trends）

### 2.1 获取趋势列表

```
GET /trends
```

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `platform` | string | 否 | 平台筛选 |
| `relevant_only` | bool | 否 | 仅返回 AI 标记为"相关"的条目 |
| `page` | int | 否 | 默认1 |
| `page_size` | int | 否 | 默认20 |

**响应示例**

```json
{
  "total": 150,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "id": 1,
      "keyword": "GPT-5发布",
      "platform": "weibo",
      "rank": 1,
      "heat_score": 5234567,
      "convergence_score": 92.5,
      "relevance_score": 85.0,
      "relevance_label": "relevant",
      "url": "https://s.weibo.com/weibo?q=GPT-5",
      "collected_at": "2026-03-22T06:00:00"
    }
  ]
}
```

---

### 2.2 获取各平台 Top N

仪表盘使用，各平台独立排序。

```
GET /trends/top-by-platform
```

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `limit` | int | 否 | 每平台返回条数，默认10 |
| `relevant_only` | bool | 否 | 仅返回相关条目 |

---

### 2.3 获取全局 Top N

```
GET /trends/top
```

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `limit` | int | 否 | 返回条数，默认20 |
| `relevant_only` | bool | 否 | 仅返回相关条目 |

---

### 2.4 获取热力图数据

24 小时内各平台热度分布。

```
GET /trends/heatmap
```

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `hours` | int | 否 | 回看小时数，默认24 |

**响应示例**

```json
{
  "platforms": ["weibo", "google", "tiktok"],
  "hours": ["06:00", "07:00", ...],
  "data": [[100, 85, ...], [50, 72, ...], [30, 45, ...]]
}
```

---

### 2.5 获取关键词动量

```
GET /trends/velocity
```

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `keyword` | string | 是 | 关键词 |
| `platform` | string | 否 | 平台筛选 |

**响应示例**

```json
{
  "keyword": "AI芯片",
  "velocity": 35.2,
  "acceleration": 12.5,
  "periods": [
    {"time": "T0", "heat": 5000},
    {"time": "T1", "heat": 3700},
    {"time": "T2", "heat": 3200}
  ]
}
```

---

### 2.6 其他趋势接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/trends/platforms` | 已注册平台列表 |
| GET | `/trends/count` | 趋势记录总数 |
| DELETE | `/trends/all` | 清空所有趋势数据 |

---

## 3. AI 洞察接口（AI）

### 3.1 单词分析

```
POST /ai/analyze
```

**Request Body**

```json
{
  "keyword": "AI芯片"
}
```

**响应示例**

```json
{
  "id": 42,
  "keyword": "AI芯片",
  "business_insight": "AI芯片供应链关键，国际形势影响市场...",
  "sentiment": "positive",
  "related_keywords": ["GPU", "NVIDIA", "芯片制造", "台积电", "算力"],
  "model": "abab6.5s-chat",
  "created_at": "2026-03-22T10:00:00"
}
```

---

### 3.2 深度分析（搜索 + AI）

手动或自动触发深度分析。包含网络搜索获取上下文 + LLM 生成结构化报告。
24 小时内同一关键词不重复分析，直接返回缓存结果。

```
POST /ai/deep-analyze
```

**Request Body**

```json
{
  "keyword": "AI芯片"
}
```

**响应示例**

```json
{
  "id": 43,
  "keyword": "AI芯片",
  "deep_analysis": {
    "background": "近期多家芯片巨头发布新一代AI加速芯片...",
    "opportunity": "国产替代加速，关注AI芯片设计公司和EDA工具链...",
    "risk": "国际制裁风险持续，高端芯片进口受限...",
    "action": "建议关注A股半导体ETF，同时跟踪国产GPU进展...",
    "sentiment": "positive"
  },
  "source_urls": [
    "https://example.com/article1",
    "https://example.com/article2"
  ],
  "search_results_count": 5,
  "analysis_type": "manual",
  "model": "abab6.5s-chat",
  "created_at": "2026-03-22T10:05:00",
  "cached": false
}
```

---

### 3.3 获取深度分析结果

```
GET /ai/deep-analyze/{keyword}
```

**Path 参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `keyword` | string | 关键词（需 URL encode） |

返回最近一次深度分析结果（如有）。

---

### 3.4 每日简报

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/ai/brief` | 手动触发生成每日简报 |
| GET | `/ai/brief/latest` | 获取最新简报 |

**简报响应示例**

```json
{
  "id": 10,
  "date": "2026-03-22",
  "content": "今日趋势概览：AI芯片赛道持续火热...",
  "model": "abab6.5s-chat",
  "created_at": "2026-03-22T08:00:00"
}
```

---

## 4. 信号接口（Signals）

### 4.1 获取近期信号

```
GET /signals/recent
```

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `hours` | int | 否 | 回看小时数，默认24 |
| `limit` | int | 否 | 返回条数，默认50 |

**响应示例**

```json
{
  "signals": [
    {
      "id": 1,
      "signal_type": "rank_jump",
      "platform": "weibo",
      "keyword": "AI芯片",
      "description": "排名跃升: 45 → 12 (↑33位)",
      "value": 33.0,
      "ai_summary": "AI芯片供应链近期受政策利好...",
      "detected_at": "2026-03-22T06:15:00"
    }
  ]
}
```

---

### 4.2 手动触发信号检测

```
POST /signals/detect
```

返回本次检测到的新信号列表。

---

## 5. 采集接口（Collector）

### 5.1 手动触发采集

```
POST /collector/collect
```

**Request Body**（可选，不传则采集所有平台）

```json
{
  "platforms": ["weibo", "google"]
}
```

**响应示例**

```json
{
  "status": "ok",
  "records_count": 70,
  "platforms": [
    {"platform": "weibo", "count": 50, "error": null},
    {"platform": "google", "count": 20, "error": null}
  ]
}
```

---

## 6. 告警接口（Alerts）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/alerts/keywords` | 获取所有监控规则 |
| POST | `/alerts/keywords` | 创建监控规则 |
| PUT | `/alerts/keywords/{id}` | 更新监控规则 |
| DELETE | `/alerts/keywords/{id}` | 删除监控规则 |

**创建规则 Request Body**

```json
{
  "keyword": "AI芯片",
  "threshold": 50000,
  "email": "user@example.com"
}
```

---

## 7. 系统接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/scheduler/status` | 调度器任务状态 |

---

## 8. 接口总览

| 模块 | 方法 | 路径 | 说明 |
|------|------|------|------|
| Trends | GET | `/trends` | 趋势列表（支持相关性过滤） |
| Trends | GET | `/trends/top` | 全局 Top N |
| Trends | GET | `/trends/top-by-platform` | 各平台 Top N |
| Trends | GET | `/trends/heatmap` | 热力图 |
| Trends | GET | `/trends/velocity` | 关键词动量 |
| Trends | GET | `/trends/platforms` | 平台列表 |
| Trends | GET | `/trends/count` | 记录总数 |
| Trends | DELETE | `/trends/all` | 清空数据 |
| AI | POST | `/ai/analyze` | 单词分析 |
| AI | POST | `/ai/deep-analyze` | 深度分析（搜索+AI） |
| AI | GET | `/ai/deep-analyze/{keyword}` | 获取深度分析结果 |
| AI | POST | `/ai/brief` | 手动生成简报 |
| AI | GET | `/ai/brief/latest` | 最新简报 |
| Signals | GET | `/signals/recent` | 近期信号 |
| Signals | POST | `/signals/detect` | 手动触发检测 |
| Collector | POST | `/collector/collect` | 手动触发采集 |
| Alerts | GET | `/alerts/keywords` | 监控规则列表 |
| Alerts | POST | `/alerts/keywords` | 创建监控 |
| Alerts | PUT | `/alerts/keywords/{id}` | 更新监控 |
| Alerts | DELETE | `/alerts/keywords/{id}` | 删除监控 |
| System | GET | `/health` | 健康检查 |
| System | GET | `/scheduler/status` | 调度器状态 |
