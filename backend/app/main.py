from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import ai as ai_router
from app.routers import alerts as alerts_router
from app.routers import collector as collector_router
from app.routers import scheduler as scheduler_router
from app.routers import trends as trends_router
from app.services.scheduler import setup_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"TrendTracker backend starting — LLM provider: {settings.llm_provider}")
    sched = setup_scheduler()
    sched.start()
    print("APScheduler started")
    yield
    # Shutdown
    sched.shutdown(wait=False)
    print("TrendTracker backend shutting down")


app = FastAPI(
    title="TrendTracker API",
    description="全网趋势聚合 + AI商业洞察平台",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", summary="健康检查", tags=["System"])
async def health():
    return {"status": "ok", "version": "0.1.0"}


app.include_router(scheduler_router.router, prefix="/api/v1/scheduler", tags=["Scheduler"])
app.include_router(collector_router.router, prefix="/api/v1/collector", tags=["Collector"])
app.include_router(trends_router.router, prefix="/api/v1/trends", tags=["Trends"])
app.include_router(ai_router.router, prefix="/api/v1/ai", tags=["AI"])
app.include_router(alerts_router.router, prefix="/api/v1/alerts", tags=["Alerts"])
