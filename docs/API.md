# API 设计文档
# TrendTracker — REST API Specification

**文档版本**: v0.1
**创建日期**: 2026-03-19
**Base URL**: `http://localhost:8000/api/v1`
**格式**: JSON
**字符集**: UTF-8

---

## 1. 通用规范

### 1.1 响应格式

所有接口统一返回以下结构：

```json
// 成功
{
  "code": 200,
  "message": "success",
  "data": { ... }
}

// 失败
{
  "code": 400,
  "message": "错误描述",
  "data": null
}
```

### 1.2 HTTP 状态码

| 状态码 | 含义 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

### 1.3 分页参数（列表接口通用）

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | 1 | 页码 |
| `page_size` | int | 20 | 每页条数，最大100 |

### 1.4 平台标识

| 值 | 平台 |
|----|------|
| `google` | Google Trends |
| `tiktok` | TikTok |
| `weibo` | 微博热搜 |
| `baidu` | 百度指数 |

---

## 2. 趋势数据接口（Trends）

### 2.1 获取仪表盘数据

首页仪表盘，返回各平台当日 Top 热词。

```
GET /trends/dashboard
```

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `date` | string | 否 | 日期 `YYYY-MM-DD`，默认今天 |
| `limit` | int | 否 | 每平台返回条数，默认10 |

**响应示例**

```json
{
  "code": 200,
  "data": {
    "date": "2026-03-19",
    "platforms": {
      "google": [
        {
          "id": 1,
          "keyword": "露营装备",
          "score": 92.5,
          "rank": 1,
          "sentiment": "positive",
          "lifecycle": "rising",
          "convergence_score": 78.3
        }
      ],
      "weibo": [ ... ],
      "tiktok": [ ... ],
      "baidu": [ ... ]
    },
    "top_convergence": [
      {
        "keyword": "露营装备",
        "convergence_score": 78.3,
        "platform_count": 3,
        "platforms": { "google": 92.5, "weibo": 85.0, "tiktok": 71.2 }
      }
    ]
  }
}
```

---

### 2.2 获取趋势列表

```
GET /trends
```

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `platform` | string | 否 | 平台筛选，多个用逗号分隔 |
| `category` | string | 否 | 品类筛选 |
| `date` | string | 否 | 日期 `YYYY-MM-DD`，默认今天 |
| `keyword` | string | 否 | 关键词模糊搜索 |
| `sort_by` | string | 否 | `score`/`convergence_score`，默认 `score` |
| `page` | int | 否 | 默认1 |
| `page_size` | int | 否 | 默认20 |

**响应示例**

```json
{
  "code": 200,
  "data": {
    "total": 150,
    "page": 1,
    "page_size": 20,
    "items": [
      {
        "id": 1,
        "keyword": "露营装备",
        "platform": "google",
        "score": 92.5,
        "rank": 1,
        "category": "消费品",
        "lifecycle": "rising",
        "sentiment": "positive",
        "convergence_score": 78.3,
        "collected_at": "2026-03-19T06:00:00"
      }
    ]
  }
}
```

---

### 2.3 获取关键词详情

```
GET /trends/{keyword}
```

**Path 参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `keyword` | string | 关键词（需 URL encode） |

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `days` | int | 否 | 历史天数，默认7 |

**响应示例**

```json
{
  "code": 200,
  "data": {
    "keyword": "露营装备",
    "latest": {
      "convergence_score": 78.3,
      "platform_count": 3,
      "lifecycle": "rising",
      "sentiment": "positive"
    },
    "history": [
      {
        "date": "2026-03-19",
        "platform": "google",
        "score": 92.5
      }
    ],
    "quick_links": {
      "1688": "https://s.1688.com/selloffer/offer_search.htm?keywords=露营装备",
      "taobao": "https://s.taobao.com/search?q=露营装备",
      "amazon": "https://www.amazon.com/s?k=camping+equipment",
      "xueqiu": "https://xueqiu.com/k?q=露营"
    },
    "latest_ai_analysis": {
      "id": 42,
      "business_insight": "该品类正处于春季爆发期...",
      "sentiment": "positive",
      "related_keywords": ["天幕", "折叠椅", "户外炊具"],
      "created_at": "2026-03-19T08:00:00"
    }
  }
}
```

---

### 2.4 获取热力图数据

```
GET /trends/heatmap
```

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `date` | string | 否 | 日期，默认今天 |
| `platform` | string | 否 | 平台筛选 |

**响应示例**

```json
{
  "code": 200,
  "data": [
    { "keyword": "露营装备", "platform": "google", "score": 92.5 },
    { "keyword": "露营装备", "platform": "weibo",  "score": 85.0 }
  ]
}
```

---

### 2.5 获取收敛评分排行

```
GET /trends/convergence
```

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `date` | string | 否 | 日期，默认今天 |
| `limit` | int | 否 | 返回条数，默认20 |
| `min_platform_count` | int | 否 | 最少出现平台数，默认2 |

---

## 3. AI 洞察接口（AI）

### 3.1 分析单个趋势

```
POST /ai/analyze
```

**Request Body**

```json
{
  "keyword": "露营装备",
  "context": {
    "platforms": ["google", "weibo"],
    "current_score": 92.5,
    "lifecycle": "rising"
  }
}
```

**响应示例**

```json
{
  "code": 200,
  "data": {
    "id": 42,
    "keyword": "露营装备",
    "business_insight": "该品类正处于春季爆发窗口期...",
    "opportunities": [
      {
        "type": "ecommerce",
        "title": "跨境电商选品",
        "detail": "建议在1688批量采购后上架速卖通/亚马逊..."
      },
      {
        "type": "content",
        "title": "内容创作选题",
        "detail": "适合制作'春季露营装备测评'系列..."
      },
      {
        "type": "investment",
        "title": "投资方向参考",
        "detail": "关注户外消费相关A股标的..."
      }
    ],
    "sentiment": "positive",
    "related_keywords": ["天幕", "折叠椅", "户外炊具", "睡袋", "帐篷"],
    "provider": "minimax",
    "created_at": "2026-03-19T10:00:00"
  }
}
```

---

### 3.2 批量分析趋势

```
POST /ai/analyze/batch
```

**Request Body**

```json
{
  "keywords": ["露营装备", "AI绘画", "新能源汽车"],
  "analysis_focus": "综合商业机会对比"
}
```

**响应示例**

```json
{
  "code": 200,
  "data": {
    "id": 43,
    "analysis_type": "batch",
    "keywords": ["露营装备", "AI绘画", "新能源汽车"],
    "business_insight": "本次分析的3个趋势中，露营装备短期变现路径最清晰...",
    "opportunities": [ ... ],
    "provider": "minimax",
    "created_at": "2026-03-19T10:05:00"
  }
}
```

---

### 3.3 获取 AI 分析历史

```
GET /ai/analyses
```

**Query 参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `keyword` | string | 否 | 按关键词筛选 |
| `analysis_type` | string | 否 | `single`/`batch` |
| `page` | int | 否 | 默认1 |
| `page_size` | int | 否 | 默认20 |

---

### 3.4 获取今日简报

```
GET /ai/brief/today
```

**响应示例**

```json
{
  "code": 200,
  "data": {
    "id": 10,
    "brief_date": "2026-03-19",
    "summary": "今日趋势概览：户外消费持续强劲，AI工具类热度环比上升35%...",
    "top_trends": [
      {
        "keyword": "露营装备",
        "convergence_score": 78.3,
        "insight": "春季爆发窗口，建议关注电商选品机会"
      }
    ],
    "is_sent": false,
    "created_at": "2026-03-19T07:00:00"
  }
}
```

---

### 3.5 获取历史简报列表

```
GET /ai/briefs
```

**Query 参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `page` | int | 默认1 |
| `page_size` | int | 默认20 |

---

### 3.6 自由对话

```
POST /ai/chat
```

**Request Body**

```json
{
  "session_id": "sess_abc123",
  "message": "根据今天的趋势，我应该重点关注哪个电商方向？",
  "include_today_trends": true
}
```

**响应示例**

```json
{
  "code": 200,
  "data": {
    "session_id": "sess_abc123",
    "message_id": 88,
    "reply": "根据今日趋势数据，以下3个方向值得重点关注...",
    "provider": "minimax"
  }
}
```

---

### 3.7 获取对话历史

```
GET /ai/chat/{session_id}
```

**响应示例**

```json
{
  "code": 200,
  "data": {
    "session_id": "sess_abc123",
    "messages": [
      { "role": "user",      "content": "根据今天的趋势...", "created_at": "..." },
      { "role": "assistant", "content": "根据今日趋势数据...", "created_at": "..." }
    ]
  }
}
```

---

## 4. 采集任务接口（Collector）

### 4.1 手动触发采集

```
POST /collector/run
```

**Request Body**

```json
{
  "platforms": ["google", "weibo"]
}
```

**响应示例**

```json
{
  "code": 200,
  "data": {
    "task_id": "task_20260319_001",
    "platforms": ["google", "weibo"],
    "status": "started",
    "message": "采集任务已启动，请稍后查询结果"
  }
}
```

---

### 4.2 查询采集状态

```
GET /collector/status
```

**响应示例**

```json
{
  "code": 200,
  "data": {
    "platforms": {
      "google":  { "status": "success", "last_run": "2026-03-19T06:00:00", "items_count": 100 },
      "weibo":   { "status": "success", "last_run": "2026-03-19T06:01:00", "items_count": 50  },
      "tiktok":  { "status": "success", "last_run": "2026-03-19T06:02:00", "items_count": 30  },
      "baidu":   { "status": "failed",  "last_run": "2026-03-19T06:03:00", "error": "Cookie expired" }
    },
    "next_scheduled_run": "2026-03-20T06:00:00"
  }
}
```

---

### 4.3 获取采集日志

```
GET /collector/logs
```

**Query 参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `platform` | string | 平台筛选 |
| `status` | string | `success`/`failed`/`partial` |
| `page` | int | 默认1 |
| `page_size` | int | 默认20 |

---

## 5. 告警接口（Alerts）

### 5.1 获取监控关键词列表

```
GET /alerts/keywords
```

---

### 5.2 添加监控关键词

```
POST /alerts/keywords
```

**Request Body**

```json
{
  "keyword": "露营",
  "platforms": ["google", "weibo"],
  "threshold_type": "score_rise",
  "threshold_value": 50,
  "note": "关注春季爆款机会"
}
```

**threshold_type 说明**

| 值 | 说明 |
|----|------|
| `score_rise` | 热度单日涨幅超过阈值（%） |
| `convergence_score` | 收敛评分超过阈值 |

---

### 5.3 更新监控关键词

```
PUT /alerts/keywords/{id}
```

---

### 5.4 删除监控关键词

```
DELETE /alerts/keywords/{id}
```

---

### 5.5 获取告警记录

```
GET /alerts/logs
```

**Query 参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `keyword` | string | 关键词筛选 |
| `page` | int | 默认1 |
| `page_size` | int | 默认20 |

---

## 6. 系统接口（System）

### 6.1 系统状态

```
GET /system/health
```

**响应示例**

```json
{
  "code": 200,
  "data": {
    "status": "ok",
    "version": "0.1.0",
    "database": "connected",
    "ai_provider": "minimax",
    "uptime_seconds": 3600
  }
}
```

---

### 6.2 获取系统配置

```
GET /system/config
```

**响应示例**

```json
{
  "code": 200,
  "data": {
    "ai_provider": "minimax",
    "collect_schedule": "0 6 * * *",
    "data_retention_days": 90,
    "alert_email": "user@example.com",
    "enabled_platforms": ["google", "weibo", "tiktok", "baidu"]
  }
}
```

---

### 6.3 更新系统配置

```
PUT /system/config
```

**Request Body**（只传需要修改的字段）

```json
{
  "collect_schedule": "0 8 * * *",
  "alert_email": "new@example.com"
}
```

---

### 6.4 数据管理统计

```
GET /system/storage
```

**响应示例**

```json
{
  "code": 200,
  "data": {
    "trend_items_count": 45000,
    "ai_analyses_count": 4500,
    "oldest_record": "2026-01-01",
    "db_size_mb": 76.3
  }
}
```

---

### 6.5 清理过期数据

```
POST /system/cleanup
```

**Request Body**

```json
{
  "before_days": 90
}
```

---

## 7. 接口总览

| 模块 | 方法 | 路径 | 说明 |
|------|------|------|------|
| Trends | GET | `/trends/dashboard` | 仪表盘数据 |
| Trends | GET | `/trends` | 趋势列表 |
| Trends | GET | `/trends/{keyword}` | 关键词详情+快捷链接 |
| Trends | GET | `/trends/heatmap` | 热力图数据 |
| Trends | GET | `/trends/convergence` | 收敛评分排行 |
| AI | POST | `/ai/analyze` | 单词分析 |
| AI | POST | `/ai/analyze/batch` | 批量分析 |
| AI | GET | `/ai/analyses` | 分析历史 |
| AI | GET | `/ai/brief/today` | 今日简报 |
| AI | GET | `/ai/briefs` | 历史简报 |
| AI | POST | `/ai/chat` | 自由对话 |
| AI | GET | `/ai/chat/{session_id}` | 对话历史 |
| Collector | POST | `/collector/run` | 手动触发采集 |
| Collector | GET | `/collector/status` | 采集状态 |
| Collector | GET | `/collector/logs` | 采集日志 |
| Alerts | GET | `/alerts/keywords` | 监控列表 |
| Alerts | POST | `/alerts/keywords` | 添加监控 |
| Alerts | PUT | `/alerts/keywords/{id}` | 更新监控 |
| Alerts | DELETE | `/alerts/keywords/{id}` | 删除监控 |
| Alerts | GET | `/alerts/logs` | 告警记录 |
| System | GET | `/system/health` | 系统状态 |
| System | GET | `/system/config` | 系统配置 |
| System | PUT | `/system/config` | 更新配置 |
| System | GET | `/system/storage` | 存储统计 |
| System | POST | `/system/cleanup` | 清理数据 |

---

*API 设计完成，共 24 个接口，下一步：开始代码实现*
