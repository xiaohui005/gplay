import logging
import sys

import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.db.migrations import run_migrations
from src.handlers.admin_data_collection import router as admin_router
from src.handlers.stock import router as stock_router
from src.handlers.watchlist import router as watchlist_router
from src.handlers.t_analysis import router as t_analysis_router
from src.middleware.error_handler import global_exception_handler, http_exception_handler
from src.services.task_scheduler import TaskScheduler
from src.collectors.registry import CollectorRegistry
from src.collectors.mock_collector import MockCollector
from src.collectors.quote_collector import QuoteCollector
from src.collectors.kline_collector import KlineCollector
from src.collectors.stock_basic_collector import StockBasicCollector
from src.collectors.news_collector import NewsCollector

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="GPlay 股票智能研判 - 数据采集模块",
    description="数据采集、清洗、调度、监控 API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)

app.include_router(admin_router)
app.include_router(stock_router)
app.include_router(watchlist_router)
app.include_router(t_analysis_router)

task_scheduler = TaskScheduler()


@app.on_event("startup")
def on_startup():
    logger.info("正在初始化数据库...")
    run_migrations()
    logger.info("数据库初始化完成")

    _register_collectors()
    logger.info("已注册采集器: %s", CollectorRegistry.list_types())

    task_scheduler.start()


@app.on_event("shutdown")
def on_shutdown():
    task_scheduler.stop()


@app.get("/")
def root():
    return {
        "service": "GPlay 股票智能研判",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "search": "/api/stocks/search?keyword=",
            "analysis": "/api/stocks/{symbol}/analysis",
            "quote": "/api/stocks/{symbol}/quote",
            "kline": "/api/stocks/{symbol}/kline?days=60",
            "news": "/api/stocks/{symbol}/news?limit=20",
            "collect": "/api/stocks/{symbol}/collect",
            "watchlist": "/api/watchlist",
            "t-analysis": "/api/stocks/{symbol}/t-analysis",
        },
    }


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


def _register_collectors():
    for cls in [MockCollector, QuoteCollector, KlineCollector, StockBasicCollector, NewsCollector]:
        CollectorRegistry.register(cls)


def main():
    uvicorn.run(
        "src.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=False,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
