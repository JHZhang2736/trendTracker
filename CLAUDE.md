## 注意事项

> 行为规则已迁移至 `.claude/rules/` 目录，包括：git 命令规范、heredoc 禁止、开发流程、PR 自动合并、commit 规范、对话记录等。

---

## 产品概述

**TrendTracker** — 全网趋势聚合 + AI商业洞察平台
- 聚合多平台热词数据，通过 AI 智能管线转化为可执行商业决策建议
- 核心管线：采集 → AI 过滤+打分 → 信号检测 → 深度分析（含网络搜索）
- MVP 阶段：个人本地使用，Docker Compose 一键部署

## 技术栈

| 层 | 选型 |
|----|------|
| 前端 | Next.js + Tailwind CSS + shadcn/ui + ECharts |
| 后端 | Python + FastAPI |
| 数据库 | MySQL 8.0 + SQLAlchemy 2.0 |
| 任务调度 | APScheduler（嵌入 FastAPI，代码解耦便于迁移 Celery） |
| AI | 多模型工厂模式（LLMFactory），初期接入 MiniMax API |
| 搜索 | 多引擎工厂模式（SearchFactory），默认 DuckDuckGo |
| 部署 | Docker Compose |

## 核心架构原则

1. **采集层插件化**：所有数据源实现 `BaseCollector` 抽象接口，通过注册中心管理，可随时插拔
2. **AI层工厂模式**：`LLMFactory` 统一创建 Provider，`.env` 配置 `LLM_PROVIDER=minimax` 即可切换模型
3. **搜索层工厂模式**：`SearchFactory` 统一创建搜索 Provider，`.env` 配置 `SEARCH_PROVIDER=duckduckgo` 即可切换
4. **职责分离**：routers（路由）/ services（业务逻辑）/ collectors（采集）/ ai（模型）/ search（搜索）各层独立
5. **AI 管线化**：采集 → 过滤+打分(Stage1) → 信号检测(Stage2) → 深度分析(Stage3) → 简报(定时)

## 关键功能

- F1 数据采集（定时自动，3个平台，分平台独立 cron）
- F2 数据展示（仪表盘、热力图、动量、收敛评分、智能过滤、快捷跳转）
- F3 AI洞察（商业建议、情感极性、相关词、每日简报、自由对话）
- F4 告警通知（关键词监控、邮件推送）
- F5 系统（Docker Compose、配置文件管理）
- F6 AI智能管线（AI过滤+重要性评分、信号检测+自动分析、深度商业分析+网络搜索）

详细内容见 `docs/PRD.md` 和 `docs/TECH.md`

---

## 开发规范

### 开发流程 / 分支策略 / Commit 规范

> 已迁移至 `.claude/rules/dev-workflow.md` 和 `.claude/rules/commit-convention.md`
> 分支命名：`feature/issue-{n}-{desc}` / `fix/issue-{n}-{desc}` / `chore/{desc}`

### 代码规范
**Python**：`ruff`（lint + import排序）+ `black`（格式化），行宽 100，配置在 `pyproject.toml`
**TypeScript**：`eslint` + `prettier`
- 命名：Python `snake_case`，类 `PascalCase`；React 组件 `PascalCase.tsx`，工具函数 `camelCase.ts`
- 层职责：routers 只做路由分发 → services 写业务逻辑 → collectors/ai/search 纯功能层，不交叉引用

### 测试策略
- Collector 必须有 mock 单元测试（数据源不稳定是最大风险）
- Service 层写单元测试，Router 写集成测试（`TestClient`）
- 前端 MVP 阶段只测核心工具函数
- 运行：`pytest tests/ -v --cov=app`

### 环境变量
- `.env.example` 提交 Git（含占位符），`.env` 加入 `.gitignore`
- 切换 AI 模型只需改 `LLM_PROVIDER=minimax` 无需改代码
- 切换搜索引擎只需改 `SEARCH_PROVIDER=duckduckgo` 无需改代码

### 自动化文档
- API 文档：FastAPI 内置 Swagger `localhost:8000/docs`，所有 Router 函数必须写 `summary`
- 每次提交后更新 Changelog：`git-cliff` 从 Conventional Commits 自动生成

详细内容见 `docs/DEV_WORKFLOW.md`
