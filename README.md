# TrendTracker

全网趋势聚合 + AI 商业洞察平台。聚合微博、Google Trends、TikTok 热词数据，通过 AI 转化为可执行商业决策建议。

## 功能概览

- **数据采集**：定时抓取微博热搜、Google Trends、TikTok 热门话题
- **趋势展示**：分平台卡片列表、仪表盘柱状图、收敛评分排行
- **AI 洞察**：单词商业分析、每日简报生成、情感极性标签
- **告警通知**：关键词热度监控 + 邮件推送

---

## 快速开始（Docker，推荐）

### 前置要求

- Docker Desktop（已启动）

### 步骤

**1. 克隆项目**

```bash
git clone https://github.com/JHZhang2736/trendTracker.git
cd trendTracker
```

**2. 配置环境变量**

```bash
cp .env.example .env
```

编辑 `.env`，至少填写以下字段：

| 字段 | 说明 |
|------|------|
| `DB_PASSWORD` | MySQL 密码，自定义即可 |
| `MINIMAX_API_KEY` | MiniMax API Key（[控制台获取](https://www.minimaxi.com/user-center/basic-information/interface-key)） |
| `MINIMAX_GROUP_ID` | MiniMax Group ID（同控制台） |
| `TIKTOK_COOKIE` | 可选，留空则跳过 TikTok 采集 |
| `SMTP_*` / `ALERT_EMAIL_TO` | 可选，留空则关闭邮件告警 |

**3. 启动所有服务**

```bash
docker compose up -d
```

首次启动会构建镜像，约需 2–3 分钟。

**4. 访问**

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:3000 |
| 后端 API | http://localhost:8000 |
| API 文档（Swagger） | http://localhost:8000/docs |

**5. 手动触发首次采集**

进入 `设置` 页面 → 点击「立即采集」，或直接请求：

```bash
curl -X POST http://localhost:8000/api/v1/collector/run
```

### 常用命令

```bash
# 查看服务日志
docker compose logs -f backend

# 停止所有服务
docker compose down

# 重建镜像（修改代码后）
docker compose build --no-cache backend
docker compose up -d
```

---

## 本地开发

### 前置要求

- Python 3.11+
- Node.js 20+
- MySQL 8.0（本地运行或 `docker compose up -d mysql` 单独启动）

### 后端

```bash
cd backend

# 安装依赖（含开发工具）
pip install -e ".[dev]"

# 配置环境变量（本地开发需将 DB_HOST 改为 127.0.0.1）
cp ../.env.example ../.env
# 编辑 .env：DB_HOST=127.0.0.1，DB_PORT=3307（若使用 Docker MySQL）

# 运行数据库迁移
alembic upgrade head

# 启动开发服务器（热重载）
uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端默认连接 `http://localhost:8000`，可通过 `NEXT_PUBLIC_API_URL` 环境变量修改。

### 运行测试

```bash
cd backend
pytest tests/ -v --cov=app
```

---

## 项目结构

```
trendTracker/
├── backend/
│   ├── app/
│   │   ├── collectors/     # 数据采集插件（微博 / Google / TikTok）
│   │   ├── ai/             # AI Provider 工厂（MiniMax）
│   │   ├── routers/        # FastAPI 路由
│   │   ├── services/       # 业务逻辑
│   │   └── models/         # SQLAlchemy 数据模型
│   └── tests/
├── frontend/
│   ├── app/                # Next.js App Router 页面
│   ├── components/         # UI 组件
│   └── lib/                # API 客户端 / 工具函数
├── docs/                   # 详细设计文档
├── docker-compose.yml
└── .env.example
```

详细架构见 [docs/TECH.md](docs/TECH.md)，产品需求见 [docs/PRD.md](docs/PRD.md)。

---

## 新增数据源

只需两个文件 + 一行注册：

1. `backend/app/collectors/{platform}.py` — 实现 `BaseCollector`
2. `backend/app/collectors/{platform}_mock.py` — Mock 版（用于测试）
3. `backend/app/collectors/__init__.py` — 注册 `registry.register(...)`
4. `frontend/lib/platform-config.ts` — 添加展示名和颜色

详见 [docs/PRD.md#平台扩展规范](docs/PRD.md)。
