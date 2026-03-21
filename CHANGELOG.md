# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Bug Fixes

- **collector**: Dedup by platform+hour + 90-day auto cleanup (#38) (#39)
- **collectors**: Update Google Trends URL + TikTok cookie auth (#40) (#41)
- **scheduler**: Collect_trends_job now persists data via run_all_collectors (#42) (#43)

### Chores

- **ci**: Add GitHub Actions CI (#4)
- **docs**: Add git-cliff config for changelog generation
- **docs**: Fix cliff.toml filter and generate initial CHANGELOG
- **ci**: Add pytest to backend CI job (#30)

### Documentation

- Add project planning documents and dev workflow
- Record Phase 1 backend skeleton conversation in history

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


