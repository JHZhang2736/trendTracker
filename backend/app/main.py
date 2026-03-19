from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"TrendTracker backend starting — LLM provider: {settings.llm_provider}")
    yield
    # Shutdown
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


# Routers will be included here as features are built
# from app.routers import trends, ai, collector, alerts
# app.include_router(trends.router, prefix="/api/v1/trends", tags=["Trends"])
