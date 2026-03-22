# 数据库设计文档
# TrendTracker — MySQL Schema Design

**文档版本**: v0.2
**最后更新**: 2026-03-22
**数据库**: MySQL 8.0

---

## 1. 表结构总览

| 表名 | 说明 | 对应功能 |
|------|------|----------|
| `trends` | 各平台采集到的趋势关键词数据（含 AI 相关性标注） | F1, F2, F6.1 |
| `platforms` | 已注册的数据源平台 | F1.6 |
| `signal_logs` | 信号检测记录（排名跃升/新上榜/热度飙升） | F6.3, F6.4 |
| `ai_insights` | AI 分析结果（商业洞察 + 深度分析报告） | F3.1, F6.5 |
| `daily_briefs` | 每日商业简报 | F3.2 |
| `keyword_alerts` | 用户关键词监控规则 | F4.1 |
| `alert_logs` | 告警触发记录 | F4.2 |

---

## 2. 详细表结构

### 2.1 trends — 趋势数据主表

存储各平台每次采集的趋势数据，包含 AI 相关性评分。

```sql
CREATE TABLE trends (
    id               BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    platform_id      INT             NOT NULL COMMENT '关联 platforms 表',
    platform         VARCHAR(50)     NOT NULL COMMENT '平台标识: weibo/google/tiktok',
    keyword          VARCHAR(200)    NOT NULL COMMENT '关键词',
    rank             SMALLINT        NULL COMMENT '排名（平台内）',
    heat_score       FLOAT           NULL COMMENT '原始热度分数',
    url              VARCHAR(500)    NULL COMMENT '原文链接',
    collected_at     DATETIME        NOT NULL COMMENT '采集时间（UTC，无时区）',

    -- AI 相关性（Stage 1 管线写入）
    relevance_score  FLOAT           NULL COMMENT 'AI 重要性评分 0-100',
    relevance_label  VARCHAR(20)     NULL COMMENT '"relevant" 或 "irrelevant"',
    relevance_reason VARCHAR(200)    NULL COMMENT 'AI 评分理由（一句话）',

    created_at       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_platform         (platform),
    INDEX idx_collected_at     (collected_at),
    INDEX idx_platform_date    (platform, collected_at),
    INDEX idx_keyword_platform (keyword, platform, collected_at),
    INDEX idx_relevance        (relevance_label)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='趋势数据主表';
```

**设计说明**：
- `relevance_score/label/reason` 由 AI 管线 Stage 1 异步写入，采集时为 NULL
- `platform` 冗余存储（不依赖 JOIN），提高查询效率
- Replace-by-hour 语义：同平台同小时内重复采集会先删后插

---

### 2.2 platforms — 平台注册表

```sql
CREATE TABLE platforms (
    id    INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name  VARCHAR(50)  NOT NULL COMMENT '平台展示名',
    slug  VARCHAR(50)  NOT NULL UNIQUE COMMENT '平台标识（唯一）',

    INDEX idx_slug (slug)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='已注册平台';
```

---

### 2.3 signal_logs — 信号检测记录

```sql
CREATE TABLE signal_logs (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    signal_type  VARCHAR(20)     NOT NULL COMMENT 'rank_jump / new_entry / heat_surge',
    platform     VARCHAR(50)     NOT NULL COMMENT '平台标识',
    keyword      VARCHAR(200)    NOT NULL COMMENT '关键词',
    description  VARCHAR(500)    NOT NULL COMMENT '人类可读描述，如"排名跃升: 45→12 (↑33位)"',
    value        FLOAT           NULL COMMENT '量化值（跃升距离/飙升倍数）',
    ai_summary   VARCHAR(500)    NULL COMMENT 'AI 自动分析摘要',
    detected_at  DATETIME        NOT NULL COMMENT '信号检测时间',

    INDEX idx_detected_at (detected_at),
    INDEX idx_keyword     (keyword),
    INDEX idx_signal_type (signal_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='趋势信号检测记录';
```

---

### 2.4 ai_insights — AI 分析结果表

存储单词分析和深度分析的结果。

```sql
CREATE TABLE ai_insights (
    id             BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    keyword        VARCHAR(200)    NOT NULL COMMENT '分析的关键词',
    trend_id       BIGINT UNSIGNED NULL COMMENT '关联的趋势记录 ID（可选）',
    insight_type   VARCHAR(50)     NOT NULL COMMENT '分析类型: business',
    content        TEXT            NOT NULL COMMENT 'JSON 编码的分析结果',
    model          VARCHAR(100)    NULL COMMENT '使用的模型',

    -- 深度分析字段（Stage 3 管线写入）
    search_context TEXT            NULL COMMENT '搜索引擎返回的原始结果 (JSON)',
    deep_analysis  TEXT            NULL COMMENT '深度分析报告全文 (JSON: background/opportunity/risk/action)',
    source_urls    TEXT            NULL COMMENT '信息来源 URLs (JSON array)',
    analysis_type  VARCHAR(20)     NULL COMMENT '"auto" 或 "manual"',

    created_at     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_keyword    (keyword),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (trend_id) REFERENCES trends(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI 分析结果';
```

**深度分析 `deep_analysis` JSON 结构**：
```json
{
  "background": "事件背景（100-200字）",
  "opportunity": "商业机会（100-200字）",
  "risk": "潜在风险（50-100字）",
  "action": "建议行动（50-100字）",
  "sentiment": "positive|negative|neutral"
}
```

---

### 2.5 daily_briefs — 每日简报表

```sql
CREATE TABLE daily_briefs (
    id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    date       DATE            NOT NULL UNIQUE COMMENT '简报日期',
    content    TEXT            NOT NULL COMMENT 'AI 生成的简报内容',
    model      VARCHAR(100)    NULL COMMENT '使用的模型',
    created_at DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='每日商业简报';
```

---

### 2.6 keyword_alerts — 关键词监控规则表

```sql
CREATE TABLE keyword_alerts (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    keyword         VARCHAR(200)    NOT NULL COMMENT '监控的关键词',
    threshold       FLOAT           NOT NULL COMMENT '热度阈值',
    email           VARCHAR(200)    NULL COMMENT '通知邮箱',
    is_active       TINYINT(1)      NOT NULL DEFAULT 1 COMMENT '是否启用',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_keyword   (keyword),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='关键词监控规则';
```

---

### 2.7 alert_logs — 告警记录表

```sql
CREATE TABLE alert_logs (
    id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    alert_id   BIGINT UNSIGNED NOT NULL COMMENT '关联的监控规则 ID',
    keyword    VARCHAR(200)    NOT NULL COMMENT '触发的关键词',
    platform   VARCHAR(50)     NULL COMMENT '触发的平台',
    heat_score FLOAT           NULL COMMENT '触发时的热度值',
    notified   TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '是否已发送通知',
    created_at DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_alert_id   (alert_id),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (alert_id) REFERENCES keyword_alerts(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='告警触发记录';
```

---

## 3. 表关系图

```
platforms ──(1:N)──► trends
                       │
                       │ keyword 逻辑关联
                       ├──────────────► signal_logs
                       └──────────────► ai_insights
                                          │
                                          │ deep_analysis (Stage 3)
                                          │ search_context (搜索结果)
                                          │ source_urls (来源链接)

keyword_alerts ──(1:N)──► alert_logs

daily_briefs   （独立，引用信号+热词数据生成）
```

**说明**：趋势数据表间主要使用 `keyword` 字符串逻辑关联，而非外键约束。原因：趋势词是采集的原始数据，不需要强引用完整性，且避免级联删除影响历史数据。

---

## 4. 关键查询示例

```sql
-- 查询当前小时各平台热词（带相关性标签）
SELECT keyword, platform, heat_score, rank, relevance_label, relevance_score
FROM trends
WHERE collected_at >= DATE_FORMAT(NOW(), '%Y-%m-%d %H:00:00')
ORDER BY platform, rank;

-- 查询仅相关条目（智能过滤）
SELECT keyword, platform, heat_score, rank, relevance_score, relevance_reason
FROM trends
WHERE relevance_label = 'relevant'
  AND collected_at >= NOW() - INTERVAL 24 HOUR
ORDER BY relevance_score DESC;

-- 查询近24h信号
SELECT signal_type, platform, keyword, description, value, ai_summary, detected_at
FROM signal_logs
WHERE detected_at >= NOW() - INTERVAL 24 HOUR
ORDER BY detected_at DESC;

-- 查询某关键词的深度分析（24h缓存检查）
SELECT keyword, deep_analysis, source_urls, analysis_type, created_at
FROM ai_insights
WHERE keyword = '某关键词'
  AND deep_analysis IS NOT NULL
  AND created_at >= NOW() - INTERVAL 24 HOUR
ORDER BY created_at DESC
LIMIT 1;

-- 查询某关键词最新 AI 分析
SELECT keyword, content, model, created_at
FROM ai_insights
WHERE keyword = '某关键词'
ORDER BY created_at DESC
LIMIT 1;
```

---

## 5. 数据量与存储估算（90天）

| 表 | 每日写入量 | 90天总量 | 估算大小 |
|----|-----------|---------|---------|
| trends | ~500条（3平台×100词×多次采集） | ~45,000行 | ~50MB |
| signal_logs | ~20条 | ~1,800行 | ~2MB |
| ai_insights | ~10条（含深度分析） | ~900行 | ~10MB |
| daily_briefs | 1条 | 90行 | <1MB |
| alert_logs | ~5条 | ~450行 | <1MB |
| **合计** | | | **~63MB** |

90天数据量极小，普通个人电脑完全无压力。

---

## 6. 数据保留策略

- 默认保留 **90天** 历史数据（可配置）
- 清理策略：定期删除 `trends`、`signal_logs`、`alert_logs` 中超期数据
- `ai_insights`、`daily_briefs` 长期保留，不参与定期清理
- 深度分析 24h 去重：同一关键词 24h 内不重复调用搜索+AI
