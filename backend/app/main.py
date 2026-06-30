import asyncio
import sys
from pathlib import Path
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.database import init_db
from app.core.logging import setup_logging

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化DB+调度器，关闭时清理"""
    setup_logging()
    logger.info("app_starting")

    # 初始化数据库
    await init_db()

    # 导入产业链数据（首次）
    from app.tasks.import_chains import import_chains
    await import_chains()

    # 启动定时任务调度器
    from app.scheduler import start_scheduler
    start_scheduler()

    logger.info("app_started", port=settings.backend_port)
    yield

    logger.info("app_stopping")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Stock V2",
        description="A股资讯分析系统",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    from app.api.v1.health import router as health_router
    from app.api.v1.stocks import router as stocks_router
    from app.api.v1.news import router as news_router
    from app.api.v1.graph import router as graph_router
    from app.api.v1.analysis import router as analysis_router
    from app.api.v1.admin import router as admin_router

    app.include_router(health_router)
    app.include_router(stocks_router)
    app.include_router(news_router)
    app.include_router(graph_router)
    app.include_router(analysis_router)
    app.include_router(admin_router)

    # 前端静态文件（生产模式）
    frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

        @app.get("/{full_path:path}")
        async def serve_spa(request: Request, full_path: str):
            """SPA catch-all：非API路径返回前端页面"""
            file_path = frontend_dist / full_path
            if file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(frontend_dist / "index.html")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    # 确保data目录存在
    Path("data").mkdir(exist_ok=True)

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.backend_port,
        reload=True,
    )
