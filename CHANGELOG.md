# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Bug Fixes

- **collector**: Dedup by platform+hour + 90-day auto cleanup (#38) (#39)
- **collectors**: Update Google Trends URL + TikTok cookie auth (#40) (#41)
- **scheduler**: Collect_trends_job now persists data via run_all_collectors (#42) (#43)
- **scheduler**: Read COLLECT_CRON env var via CronTrigger.from_crontab (#46) (#48)
- **collector**: Log errors per-platform + expose platforms field in run response (#50) (#51)
- **docker**: Remove invalid pull_policy from build blocks
- **dashboard**: 热词总数改用全量计数 + 禁用 fetch 缓存 (#59) (#60)
- **relevance**: 智能过滤仅保留 relevant + 简报使用相关内容
- **trends**: 趋势列表按 platform+keyword 去重
- **relevance**: LLM 失败时不标记为 relevant
- **relevance**: 强化 prompt + index 匹配 + 调试日志
- **relevance**: MiniMax chat 设置 max_tokens=2048 防截断
- **relevance**: 修复未匹配关键词无标签 + 增加调试日志
- **relevance**: 按数组位置匹配替代关键词文本匹配
- **relevance**: 极简化 LLM 输出为序号列表 [1,3,7]
- **relevance**: 简化 prompt 修复 MiniMax 全返回空数组 (#77)
- **ui**: 默认展开分析详情、默认过滤趋势、清空含分析数据 (#82)
- **ui**: 数据源状态显示最近拉取时间 (#90) (#91)
- **search**: 空结果重试 + Provider 自动降级 (#106)
- **ci**: Changelog job uses PR instead of direct push to main (#109) (#110)
- **ci**: Use peter-evans/create-pull-request for changelog (#109) (#111)

### Chores

- **ci**: Add GitHub Actions CI (#4)
- **docs**: Add git-cliff config for changelog generation
- **docs**: Fix cliff.toml filter and generate initial CHANGELOG
- **ci**: Add pytest to backend CI job (#30)
- **docker**: Cache pip install layer — copy pyproject.toml before source (#52)
- **docker**: Pull_policy if_not_present — skip registry check when image cached locally
- **docker**: Install production deps only, exclude dev tools from image
- **hooks**: 添加 pre-commit ruff + black 检查 hook
- 补充 skills 配置、CHANGELOG、config 改进 (#61)
- **db**: 添加 signal_logs 表迁移脚本 (#71)
- 清理 main 积压改动 + 工程化优化 (#108)

### Documentation

- Add project planning documents and dev workflow
- Record Phase 1 backend skeleton conversation in history
- Mark medium-priority frontend tasks as done in TODO.md
- Mark low-priority tech debt items as done in TODO.md
- 添加 README（本地开发 + Docker 部署指南）

### Features

- **infra**: Phase 0 base environment scaffold (#2)
- **backend**: Add SQLAlchemy 2.0 ORM models for 8 tables (#9)
- **backend**: Add BaseCollector, CollectorRegistry, WeiboMockCollector (#10)
- **backend**: Add BaseLLMProvider, LLMFactory, MiniMaxProvider stub (#11)
- **backend**: Embed APScheduler in FastAPI lifespan + /api/v1/scheduler/status (#12)
- **backend**: Add Alembic initial migration for 8 tables (#13) (#24)
- **backend**: Router 骨架 — /collector/run + /trends 基础接口 (#26)
- **frontend**: Phase 2 — 前端骨架（页面路由 + 布局 + API层） (#25)
- **backend**: WeiboCollector real API + DB persistence + trends from DB (#16) (#27)
- 仪表盘热力图 ECharts + /trends/heatmap 接口 (#17) (#28)
- **backend**: 收敛评分算法 + /trends/top 接口 (#18) (#29)
- **backend**: AI keyword analysis — MiniMax real API + /ai/analyze endpoint (#19) (#31)
- 每日简报生成 — AI汇总 + 邮件推送 + APScheduler 08:00定时任务 (#20) (#32)
- **backend**: GoogleTrendsCollector — RSS采集 Top20 + geo支持 (#22) (#33)
- **backend**: TikTokCollector — Creative Center API 热门话题采集 (#23) (#34)
- 关键词监控 + 邮件告警 — AlertRule CRUD + 采集后自动检查阈值 (#21) (#35)
- **trends**: Per-platform convergence scoring + dashboard charts (#36) (#37)
- **frontend**: Implement AI insights, alerts, and dashboard stats pages (#44) (#45)
- **trends**: CTE-scoped platform max + convergence_score ranking (#53) (#54)
- **settings**: 设置页 — 调度器/数据源/AI/邮件状态 + 清空数据 (#55) (#56)
- **trends**: 趋势列表改为分平台卡片布局 + 移除热力图 (#57) (#58)
- **google**: 采集多地区(US/TW/JP)并去重合并 + 趋势列表加回立即采集按钮 + 修复排名编号
- **google**: 调整默认地区为 US/IN/JP/KR/IL/SG（技术商业信号最强6区）
- **tiktok**: 采集多地区(US/GB/JP/BR/ID/TH)并去重合并
- **tiktok**: 翻页采集(2页×50条) + limit提升到50，增加数据量
- **signals**: 采集后自动信号检测 (#63)
- **scheduler**: 采集频率分级 per-platform cron (#66)
- **signals**: AI 信号驱动分析 + 信号简报 (#67)
- 趋势速度/加速度 + 前端 UX 增强 (#70)
- **relevance**: AI 信息相关性过滤模块 (#72) (#73)
- **pipeline**: AI 深度分析 + 搜索层 + 评分升级 (#75)
- **deep-analysis**: 深度分析独立页面 + 列表接口 (#79)
- **prompts**: 优化相关性和深度分析 prompt (#80)
- **deep-analysis**: 多视角商业分析 + prompt 优化 (#81)
- **ai**: 自动分析比例化 + 相关性 prompt 优化商业导向 (#83)
- **search**: 新增 Bing 搜索 Provider + Google Provider (#84) (#85)
- 删除告警监控 + AI关键词分析功能 (#86) (#87)
- **email**: 恢复邮件推送功能 + 设置页面显示配置状态 (#88) (#89)
- **brief**: 简报 Prompt 个性化 + 引用深度分析 (#92) (#93)
- **analysis**: 新闻简介模式 + 设置页面模式切换 (#94) (#95)
- **search**: 搜索 Provider 指数退避重试 + 批量分析节流 (#98) (#99)
- **settings**: 信息源开关，控制采集与展示 (#100) (#101)
- **collector**: SSE 实时推送采集管线进度 (#103)

### Refactor

- **frontend**: Replace local PLATFORM_LABELS with getPlatformMeta (#47) (#49)
- **analysis**: 统一返回概述+商业分析，设置控制商业分析显隐 (#96)
- **analysis**: 统一返回概述+商业分析，设置控制显隐 (#96) (#97)


