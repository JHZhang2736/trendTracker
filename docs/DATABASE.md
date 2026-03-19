# 数据库设计文档
# TrendTracker — MySQL Schema Design

**文档版本**: v0.1
**创建日期**: 2026-03-19
**数据库**: MySQL 8.0

---

## 1. 表结构总览

| 表名 | 说明 | 对应功能 |
|------|------|----------|
| `trend_items` | 各平台采集到的趋势关键词原始数据 | F1, F2 |
| `convergence_scores` | 跨平台收敛评分计算结果 | F2.4 |
| `ai_analyses` | AI分析结果（商业洞察、情感标签、相关词） | F3 |
| `daily_briefs` | 每日商业简报 | F3.3 |
| `chat_messages` | 自由对话历史记录 | F3.5 |
| `watch_keywords` | 用户关键词监控列表 | F4.1 |
| `alert_logs` | 告警触发记录 | F4 |
| `collect_logs` | 采集任务执行日志 | F1.6 |

---

## 2. 详细表结构

### 2.1 trend_items — 趋势数据主表

存储各平台每次采集的原始趋势数据，是整个系统的核心数据表。

```sql
CREATE TABLE trend_items (
    id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    keyword       VARCHAR(255)    NOT NULL COMMENT '关键词',
    platform      VARCHAR(50)     NOT NULL COMMENT '来源平台: google/tiktok/weibo/baidu/alibaba',
    score         DECIMAL(10, 2)  NOT NULL DEFAULT 0 COMMENT '热度分数，归一化到 0-100',
    rank          SMALLINT        NULL COMMENT '排名（部分平台有排名）',
    category      VARCHAR(100)    NULL COMMENT '品类标签: 消费品/科技/娱乐/金融等',
    lifecycle     VARCHAR(20)     NULL COMMENT '生命周期阶段: rising/peak/declining/emerging',
    sentiment     VARCHAR(20)     NULL COMMENT '情感极性: positive/neutral/negative',
    raw_data      JSON            NULL COMMENT '原始响应数据，保留备查',
    collected_at  DATETIME        NOT NULL COMMENT '采集时间',
    created_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_keyword          (keyword),
    INDEX idx_platform         (platform),
    INDEX idx_collected_at     (collected_at),
    INDEX idx_platform_date    (platform, collected_at),
    INDEX idx_keyword_platform (keyword, platform, collected_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='趋势数据主表';
```

**设计说明**：
- `score` 归一化到 0-100，便于跨平台对比
- `raw_data` JSON 字段保留原始响应，方便后续补充新字段无需迁移
- `idx_keyword_platform` 联合索引支持"某词在某平台的历史趋势"高频查询

---

### 2.2 convergence_scores — 收敛评分表

每次采集后计算跨平台收敛评分，记录历史变化。

```sql
CREATE TABLE convergence_scores (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    keyword         VARCHAR(255)   NOT NULL COMMENT '关键词',
    score           DECIMAL(5, 2)  NOT NULL COMMENT '收敛评分 0-100',
    platform_count  TINYINT        NOT NULL COMMENT '出现的平台数量',
    platforms       JSON           NOT NULL COMMENT '出现的平台列表及各平台分数',
    calculated_at   DATETIME       NOT NULL COMMENT '计算时间',
    created_at      DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_keyword        (keyword),
    INDEX idx_score          (score DESC),
    INDEX idx_calculated_at  (calculated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='跨平台收敛评分';
```

**示例 platforms 字段**：
```json
{
  "google": 85.0,
  "tiktok": 72.3,
  "weibo": 91.0
}
```

---

### 2.3 ai_analyses — AI分析结果表

存储对单个趋势词的 AI 分析结果，包含商业建议、情感标签、相关词。

```sql
CREATE TABLE ai_analyses (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    keyword         VARCHAR(255)   NOT NULL COMMENT '分析的关键词',
    analysis_type   VARCHAR(50)    NOT NULL COMMENT '分析类型: single/batch/related_words',
    provider        VARCHAR(50)    NOT NULL COMMENT 'AI提供商: minimax/deepseek/qwen',
    model           VARCHAR(100)   NOT NULL COMMENT '使用的模型名称',

    -- 分析结果
    business_insight    TEXT        NULL COMMENT '商业机会解读',
    opportunities       JSON        NULL COMMENT '多维度机会列表',
    sentiment           VARCHAR(20) NULL COMMENT '情感极性: positive/neutral/negative',
    related_keywords    JSON        NULL COMMENT '相关词扩展列表',
    raw_response        TEXT        NULL COMMENT 'AI原始响应',

    -- 关联数据快照
    trend_context       JSON        NULL COMMENT '分析时的趋势数据快照',

    tokens_used     INT            NULL COMMENT '消耗token数',
    created_at      DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_keyword      (keyword),
    INDEX idx_type         (analysis_type),
    INDEX idx_created_at   (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI分析结果';
```

**示例 opportunities 字段**：
```json
[
  {"type": "ecommerce", "title": "跨境电商选品", "detail": "建议上架..."},
  {"type": "content",   "title": "内容创作选题", "detail": "适合制作..."},
  {"type": "investment","title": "投资方向参考", "detail": "关注相关板块..."}
]
```

---

### 2.4 daily_briefs — 每日简报表

存储每日自动生成的趋势商业简报。

```sql
CREATE TABLE daily_briefs (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    brief_date   DATE            NOT NULL COMMENT '简报日期',
    top_trends   JSON            NOT NULL COMMENT 'Top趋势列表及摘要',
    summary      TEXT            NOT NULL COMMENT 'AI生成的整体简报内容',
    provider     VARCHAR(50)     NOT NULL COMMENT '生成使用的AI提供商',
    is_sent      TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '是否已推送邮件',
    sent_at      DATETIME        NULL COMMENT '邮件发送时间',
    created_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE INDEX idx_brief_date (brief_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='每日商业简报';
```

---

### 2.5 chat_messages — 自由对话记录表

存储用户与 AI 自由对话的历史消息。

```sql
CREATE TABLE chat_messages (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id   VARCHAR(64)     NOT NULL COMMENT '会话ID',
    role         VARCHAR(20)     NOT NULL COMMENT 'user / assistant',
    content      TEXT            NOT NULL COMMENT '消息内容',
    provider     VARCHAR(50)     NULL COMMENT 'AI提供商',
    tokens_used  INT             NULL COMMENT '消耗token数',
    created_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_session_id  (session_id),
    INDEX idx_created_at  (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='自由对话历史';
```

---

### 2.6 watch_keywords — 关键词监控表

用户自定义的关键词监控规则。

```sql
CREATE TABLE watch_keywords (
    id               BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    keyword          VARCHAR(255)   NOT NULL COMMENT '监控的关键词',
    platforms        JSON           NOT NULL COMMENT '监控的平台列表，空=全部',
    threshold_type   VARCHAR(50)    NOT NULL COMMENT '触发类型: score_rise/convergence_score',
    threshold_value  DECIMAL(10,2)  NOT NULL COMMENT '触发阈值',
    is_active        TINYINT(1)     NOT NULL DEFAULT 1 COMMENT '是否启用',
    note             VARCHAR(500)   NULL COMMENT '用户备注',
    created_at       DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_keyword   (keyword),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='关键词监控规则';
```

---

### 2.7 alert_logs — 告警记录表

记录每次告警触发的历史。

```sql
CREATE TABLE alert_logs (
    id               BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    watch_keyword_id BIGINT UNSIGNED NOT NULL COMMENT '触发的监控规则ID',
    keyword          VARCHAR(255)    NOT NULL COMMENT '触发的关键词',
    trigger_type     VARCHAR(50)     NOT NULL COMMENT '触发类型',
    trigger_value    DECIMAL(10,2)   NOT NULL COMMENT '触发时的实际值',
    threshold_value  DECIMAL(10,2)   NOT NULL COMMENT '设定的阈值',
    platform         VARCHAR(50)     NULL COMMENT '触发的平台',
    is_notified      TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '是否已发送通知',
    notified_at      DATETIME        NULL COMMENT '通知发送时间',
    created_at       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_watch_keyword_id (watch_keyword_id),
    INDEX idx_keyword          (keyword),
    INDEX idx_created_at       (created_at),
    FOREIGN KEY (watch_keyword_id) REFERENCES watch_keywords(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='告警触发记录';
```

---

### 2.8 collect_logs — 采集任务日志表

记录每次定时采集任务的执行状态，方便排查失败原因。

```sql
CREATE TABLE collect_logs (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    platform     VARCHAR(50)    NOT NULL COMMENT '采集平台',
    status       VARCHAR(20)    NOT NULL COMMENT 'success / failed / partial',
    items_count  INT            NOT NULL DEFAULT 0 COMMENT '成功采集的条数',
    error_msg    TEXT           NULL COMMENT '失败时的错误信息',
    duration_ms  INT            NULL COMMENT '采集耗时（毫秒）',
    started_at   DATETIME       NOT NULL COMMENT '开始时间',
    finished_at  DATETIME       NULL COMMENT '结束时间',
    created_at   DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_platform    (platform),
    INDEX idx_status      (status),
    INDEX idx_started_at  (started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='采集任务执行日志';
```

---

## 3. 表关系图

```
trend_items ──────────────────────────────────────────┐
     │                                                 │
     │ keyword 关联（逻辑关联，无外键）                │
     ▼                                                 ▼
convergence_scores                              ai_analyses
     │
     │ keyword 关联（逻辑关联）
     ▼
watch_keywords ──── (id) ────► alert_logs

daily_briefs        （独立，引用 trend_items 数据快照存入 JSON）
chat_messages       （独立会话记录）
collect_logs        （独立任务日志）
```

**说明**：趋势数据表间使用 `keyword` 字符串逻辑关联，而非外键约束。原因：趋势词是采集的原始数据，不需要强引用完整性，且避免级联删除影响历史数据。

---

## 4. 关键查询示例

```sql
-- 查询今日各平台 Top10 热词
SELECT keyword, platform, score, rank, sentiment
FROM trend_items
WHERE DATE(collected_at) = CURDATE()
ORDER BY platform, score DESC
LIMIT 10;

-- 查询某关键词近7天热度趋势（折线图数据）
SELECT DATE(collected_at) AS date, platform, AVG(score) AS avg_score
FROM trend_items
WHERE keyword = '露营'
  AND collected_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY DATE(collected_at), platform
ORDER BY date;

-- 查询今日收敛评分 Top20
SELECT keyword, score, platform_count, platforms, calculated_at
FROM convergence_scores
WHERE DATE(calculated_at) = CURDATE()
ORDER BY score DESC
LIMIT 20;

-- 查询某关键词最新 AI 分析
SELECT business_insight, opportunities, sentiment, related_keywords
FROM ai_analyses
WHERE keyword = '露营'
ORDER BY created_at DESC
LIMIT 1;
```

---

## 5. 数据量与存储估算（90天）

| 表 | 每日写入量 | 90天总量 | 估算大小 |
|----|-----------|---------|---------|
| trend_items | ~500条（5平台×100词） | ~45,000行 | ~50MB |
| convergence_scores | ~100条 | ~9,000行 | ~5MB |
| ai_analyses | ~50条 | ~4,500行 | ~20MB |
| daily_briefs | 1条 | 90行 | <1MB |
| collect_logs | ~10条 | ~900行 | <1MB |
| **合计** | | | **~76MB** |

90天数据量极小，普通个人电脑完全无压力。

---

## 6. 数据保留策略

- 默认保留 **90天** 历史数据（可配置文件调整）
- 清理策略：定期删除 `trend_items`、`convergence_scores`、`collect_logs` 中超期数据
- `ai_analyses`、`daily_briefs`、`chat_messages` 长期保留，不参与定期清理
