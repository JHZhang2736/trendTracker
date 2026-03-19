# 开发工作流规范
# TrendTracker — Development Workflow

**文档版本**: v0.1
**创建日期**: 2026-03-19

---

## 1. 开发顺序

采用 **基础设施优先 → 垂直切片** 策略：先跑通整条链路，再逐功能迭代。

### Phase 0 — 基础环境（Day 1）
```
目标：docker compose up 后三个服务全部健康运行，无任何业务功能
```
1. 初始化 Git 仓库，创建 `.gitignore`、`README.md`
2. 编写 `docker-compose.yml`（mysql / backend / frontend 三服务）
3. FastAPI 入口 `main.py` — 仅包含 `/health` 接口
4. Next.js 初始化 — 仅首页显示 "TrendTracker"
5. SQLAlchemy 连接 MySQL，Alembic 初始化迁移

**完成标准**：`curl localhost:8000/health` 返回 `{"status":"ok"}`，`localhost:3000` 正常渲染

---

### Phase 1 — 后端骨架（Day 2-3）
```
目标：8张表建好，采集层+AI层抽象接口实现，APScheduler 跑起来
```
1. SQLAlchemy Models（8张表）+ Alembic 首次迁移
2. `BaseCollector` 抽象类 + `CollectorRegistry`
3. `WeiboCollector` 实现（最简单，验证插件机制）
4. `BaseLLMProvider` 抽象类 + `LLMFactory` + `MiniMaxProvider`
5. APScheduler 接入，定时任务触发采集
6. 路由层骨架（空实现，返回 mock 数据）

**完成标准**：手动调用 `POST /api/v1/collector/run` 能采集微博热搜并写入 MySQL

---

### Phase 2 — 前端骨架（Day 4）
```
目标：页面路由、布局、shadcn 组件库跑通，对接后端 /health
```
1. Next.js App Router 页面结构（Dashboard / Trends / AI / Alerts）
2. 侧边栏导航组件（shadcn）
3. API 请求层封装（`lib/api.ts`，统一错误处理）
4. 全局状态管理（React Context 或 Zustand，简单为主）

**完成标准**：四个页面路由可访问，侧边栏正常，能调通后端接口

---

### Phase 3-N — 垂直切片（按 Issue 开发）
```
每个 Issue = 一个完整功能（后端接口 + 前端页面/组件）
```
推荐顺序：
| Issue | 功能 | 价值 |
|-------|------|------|
| #1 | 微博热搜采集 + 趋势列表页 | 跑通完整数据链路 |
| #2 | Google Trends 采集 | 增加数据源 |
| #3 | 仪表盘热力图（ECharts） | 核心展示功能 |
| #4 | 收敛评分计算 + 展示 | 核心算法 |
| #5 | AI 单词分析（MiniMax） | 核心 AI 功能 |
| #6 | 每日简报生成 | AI 增值功能 |
| #7 | 关键词监控 + 邮件告警 | 告警功能 |
| #8 | TikTok 采集 | 扩展数据源 |
| #9 | 百度指数采集 | 扩展数据源 |
| #10 | 情感极性标签 + 相关词扩展 | F3.7/F3.8 |

---

## 2. 仓库管理规范

### 2.1 分支策略（GitHub Flow 简化版）

```
main          ← 永远可部署，只接受 PR 合并
  └── feature/issue-1-weibo-collector    ← 功能分支
  └── feature/issue-3-dashboard-heatmap
  └── fix/issue-11-scheduler-crash
  └── chore/update-dependencies
```

**规则**：
- `main` 禁止直接 push
- 每个 Issue 开一个功能分支，完成后 PR 合并回 main
- 合并方式：**Squash and Merge**（保持 main 历史干净）

### 2.2 分支命名

```
feature/issue-{n}-{short-desc}    # 新功能
fix/issue-{n}-{short-desc}        # Bug 修复
chore/{short-desc}                # 工程类（依赖、配置等）
docs/{short-desc}                 # 文档
```

### 2.3 Commit 规范（Conventional Commits）

格式：`<type>(<scope>): <subject>`

| type | 用途 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `refactor` | 重构（不影响功能） |
| `test` | 测试相关 |
| `chore` | 依赖更新、配置、CI |
| `docs` | 文档 |
| `style` | 格式化，不影响逻辑 |

示例：
```
feat(collector): add WeiboCollector with top 50 hot search
fix(scheduler): prevent duplicate job registration on reload
chore(deps): upgrade fastapi to 0.115
docs(api): update /trends/dashboard response schema
```

### 2.4 Issue 管理

每个 Issue 包含：
```markdown
## 目标
简述要实现的功能

## 验收标准（AC）
- [ ] 后端接口返回正确数据
- [ ] 前端展示符合设计
- [ ] 单元测试通过

## 技术备注
实现思路、注意事项
```

**Labels**：`feature` / `bug` / `enhancement` / `blocked` / `backend` / `frontend`

---

## 3. 代码规范

### 3.1 Python 后端

**工具链**：
| 工具 | 用途 | 配置 |
|------|------|------|
| `ruff` | Lint + Import 排序 | `pyproject.toml` |
| `black` | 代码格式化 | `pyproject.toml` |
| `mypy` | 静态类型检查（可选，MVP 阶段宽松） | 仅检查 `app/` |

**`pyproject.toml` 关键配置**：
```toml
[tool.black]
line-length = 100
target-version = ["py311"]

[tool.ruff]
line-length = 100
select = ["E", "F", "I"]  # pycodestyle + pyflakes + isort

[tool.mypy]
python_version = "3.11"
ignore_missing_imports = true
```

**命名约定**：
- 文件/模块：`snake_case.py`
- 类名：`PascalCase`
- 函数/变量：`snake_case`
- 常量：`UPPER_SNAKE_CASE`
- Pydantic Schema：`XxxRequest` / `XxxResponse`
- SQLAlchemy Model：`XxxModel`（避免与 Pydantic 冲突）

**目录结构约定**：
```
routers/    ← 只做路由分发，不写业务逻辑
services/   ← 所有业务逻辑，调用 collectors/ai/models
collectors/ ← 纯数据采集，不依赖 services
models/     ← SQLAlchemy ORM 模型，不含业务逻辑
schemas/    ← Pydantic 请求/响应模型
```

### 3.2 TypeScript 前端

**工具链**：
| 工具 | 用途 |
|------|------|
| `eslint` + `@typescript-eslint` | Lint |
| `prettier` | 格式化 |
| `next/font` | 字体 |

**`.eslintrc` 关键规则**：
```json
{
  "rules": {
    "no-unused-vars": "warn",
    "@typescript-eslint/no-explicit-any": "warn",
    "react-hooks/exhaustive-deps": "warn"
  }
}
```

**命名约定**：
- 组件文件：`PascalCase.tsx`（如 `TrendHeatmap.tsx`）
- 工具函数文件：`camelCase.ts`（如 `formatScore.ts`）
- 类型定义：`types/` 目录，接口名 `I` 前缀（可选）
- API 函数：`lib/api/trends.ts`，函数名 `fetchXxx` / `postXxx`

**组件规范**：
```tsx
// 每个组件文件只导出一个默认组件
// Props 用 interface 定义，放在组件上方
interface TrendCardProps {
  keyword: string
  score: number
  platform: string
}

export default function TrendCard({ keyword, score, platform }: TrendCardProps) {
  // ...
}
```

---

## 4. 测试策略

### 4.1 后端测试（pytest）

**测试范围**（MVP 阶段务实为主）：
| 层 | 测试类型 | 优先级 |
|----|----------|--------|
| Collectors | 单元测试（mock HTTP）| 高 |
| Services | 单元测试（mock DB）| 高 |
| Routers | 集成测试（TestClient）| 中 |
| AI Layer | 单元测试（mock API 调用）| 中 |

**目录结构**：
```
backend/tests/
├── unit/
│   ├── test_weibo_collector.py
│   ├── test_convergence_service.py
│   └── test_llm_factory.py
└── integration/
    ├── test_trends_router.py
    └── conftest.py          # pytest fixtures (TestClient, mock DB)
```

**运行命令**：
```bash
pytest tests/ -v --cov=app --cov-report=term-missing
```

### 4.2 前端测试（MVP 阶段从简）

MVP 阶段**不强制写前端测试**，仅对核心工具函数写单元测试：
```
frontend/src/__tests__/
└── lib/
    ├── formatScore.test.ts
    └── convergenceColor.test.ts
```

### 4.3 测试约定

- 每个 Collector 必须有 mock 测试（数据源不稳定，测试是安全网）
- 新增 Service 方法时同步写测试
- CI 不通过测试不允许合并 PR（本地用 pre-commit hook 保证）

---

## 5. 自动化文档系统

### 5.1 API 文档（零成本，FastAPI 内置）

FastAPI 自动生成：
- **Swagger UI**：`http://localhost:8000/docs`
- **ReDoc**：`http://localhost:8000/redoc`
- **OpenAPI JSON**：`http://localhost:8000/openapi.json`

要求：所有 Router 函数必须写 `summary` 和 `description`：
```python
@router.get("/dashboard", summary="获取仪表盘数据",
            description="返回热力图数据、各平台 Top 热词、收敛评分 Top20")
async def get_dashboard() -> DashboardResponse:
    ...
```

### 5.2 Changelog 自动生成

使用 `git-cliff` 从 Conventional Commits 自动生成 `CHANGELOG.md`：
```bash
# 安装
cargo install git-cliff  # 或 pip install git-cliff

# 生成
git cliff --output CHANGELOG.md
```

`cliff.toml` 配置：只收录 `feat` / `fix` / `refactor`，过滤 `chore` / `docs`。

### 5.3 数据库 Schema 同步

每次 Alembic 生成新迁移后，在 PR 描述中附上变更说明。`DATABASE.md` 在有表结构变更时手动同步（避免过度自动化）。

---

## 6. 本地开发环境

### 6.1 Pre-commit Hook（质量门禁）

```bash
pip install pre-commit
```

`.pre-commit-config.yaml`：
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.0.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-merge-conflict
```

```bash
pre-commit install  # 安装钩子
```

### 6.2 环境变量管理

```
.env.example    ← 提交到 Git（含所有 Key 的占位符，无真实值）
.env            ← 本地真实配置，加入 .gitignore
```

`.env.example`：
```env
# Database
DB_HOST=mysql
DB_PORT=3306
DB_NAME=trendtracker
DB_USER=root
DB_PASSWORD=your_password_here

# AI
LLM_PROVIDER=minimax
MINIMAX_API_KEY=your_minimax_key_here
MINIMAX_GROUP_ID=your_group_id_here

# Scheduler
COLLECT_CRON=0 6 * * *   # 每天 06:00 采集

# Email (alerts)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password_here
ALERT_EMAIL_TO=your_email@gmail.com
```

### 6.3 快速启动命令

```bash
# 启动所有服务
docker compose up -d

# 查看日志
docker compose logs -f backend

# 进入后端 shell（调试）
docker compose exec backend bash

# 执行数据库迁移
docker compose exec backend alembic upgrade head

# 手动触发采集（开发调试）
curl -X POST http://localhost:8000/api/v1/collector/run

# 重建后端镜像（代码变更后）
docker compose up -d --build backend
```

---

## 7. 开发节奏建议

```
每个 Issue 的开发流程：

1. 从 main 创建功能分支
   git checkout -b feature/issue-1-weibo-collector

2. 先写后端：Model → Service → Router → 接口测试 (curl/swagger)

3. 再写前端：API 类型定义 → API 调用函数 → 组件 → 页面集成

4. 本地 docker compose up 验证完整链路

5. 提交 PR，描述填写：功能说明 + 截图/curl 输出

6. Squash merge 回 main
```

---

## 8. 文件命名速查

| 类型 | 规范 | 示例 |
|------|------|------|
| Python 模块 | `snake_case.py` | `weibo_collector.py` |
| Python 测试 | `test_{module}.py` | `test_weibo_collector.py` |
| React 组件 | `PascalCase.tsx` | `TrendHeatmap.tsx` |
| Next.js 页面 | `page.tsx`（App Router） | `app/trends/page.tsx` |
| API 工具函数 | `camelCase.ts` | `lib/api/trends.ts` |
| 样式（如有） | `PascalCase.module.css` | `TrendCard.module.css` |
| Alembic 迁移 | 自动生成 | `001_initial_schema.py` |
| Docker 文件 | 固定 | `Dockerfile`, `docker-compose.yml` |

