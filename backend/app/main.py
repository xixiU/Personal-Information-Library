"""FastAPI application entry point."""
import logging
import os
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.core.scheduler import get_scheduler
from app.api import sources, tasks, results, refine, plugins, categories, dashboard
from app.api import notification_channels, notification_rules
from app.api import feedback, interest_points, interest_discovery
from app.api import highlights

# 配置日志
log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

logging.basicConfig(level=log_level, format=log_format)

# 文件日志
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(log_dir, exist_ok=True)
file_handler = RotatingFileHandler(
    os.path.join(log_dir, "app.log"),
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
    encoding="utf-8",
)
file_handler.setLevel(log_level)
file_handler.setFormatter(logging.Formatter(log_format))
logging.getLogger().addHandler(file_handler)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting application...")
    init_db()

    # 启动调度器
    scheduler = get_scheduler()
    await scheduler.start()
    logger.info("Scheduler started")

    yield

    # Shutdown
    logger.info("Shutting down application...")
    await scheduler.stop()
    logger.info("Scheduler stopped")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(categories.router)
app.include_router(sources.router)
app.include_router(tasks.router)
app.include_router(results.router)
app.include_router(refine.router)
app.include_router(plugins.router)
app.include_router(dashboard.router)
app.include_router(notification_channels.router)
app.include_router(notification_rules.router)
app.include_router(feedback.router)
app.include_router(interest_discovery.router)
app.include_router(interest_points.router)
app.include_router(highlights.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import sys
    import os
    import uvicorn

    # 将 backend/ 目录加入 sys.path，使 `python app/main.py` 可以直接运行
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, backend_dir)
    os.chdir(backend_dir)

    uvicorn.run(app, host="0.0.0.0", port=8000)
