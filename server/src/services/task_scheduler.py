import datetime
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.db.database import SessionLocal
from src.handlers.technical_analysis import save_technical_analysis_for_symbol
from src.handlers.stock import collect_stock
from src.models import UserWatchlist
from src.services.collection_service import CollectionService

logger = logging.getLogger(__name__)

WEEKEND_DAYS = {5, 6}  # Saturday=5, Sunday=6


class TaskScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.service = CollectionService()
        self._started = False

    @staticmethod
    def _is_weekend() -> bool:
        return datetime.datetime.now().weekday() in WEEKEND_DAYS

    def start(self):
        if self._started:
            return
        self._register_jobs()
        self.scheduler.start()
        self._started = True
        logger.info("任务调度器已启动")

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            self._started = False
            logger.info("任务调度器已停止")

    def _register_jobs(self):
        self.scheduler.add_job(
            self._collect_stock_basic,
            CronTrigger(hour=8, minute=0),
            id="collect_stock_basic_daily",
            name="股票基础信息同步",
            replace_existing=True,
        )

        self.scheduler.add_job(
            self._collect_trade_status,
            CronTrigger(hour=8, minute=30),
            id="collect_trade_status_morning",
            name="交易状态同步-盘前",
            replace_existing=True,
        )
        self.scheduler.add_job(
            self._collect_trade_status,
            CronTrigger(hour=12, minute=0),
            id="collect_trade_status_midday",
            name="交易状态同步-盘中",
            replace_existing=True,
        )
        self.scheduler.add_job(
            self._collect_trade_status,
            CronTrigger(hour=15, minute=30),
            id="collect_trade_status_afternoon",
            name="交易状态同步-盘后",
            replace_existing=True,
        )

        self.scheduler.add_job(
            self._collect_quote,
            CronTrigger(minute="*/5"),
            id="collect_quote_5min",
            name="延迟行情采集 (5分钟)",
            replace_existing=True,
        )

        self.scheduler.add_job(
            self._collect_kline,
            CronTrigger(hour=16, minute=30),
            id="collect_kline_daily",
            name="日 K 采集",
            replace_existing=True,
        )

        self.scheduler.add_job(
            self._collect_financial,
            CronTrigger(hour=7, minute=0),
            id="collect_financial_daily",
            name="财务数据采集",
            replace_existing=True,
        )

        self.scheduler.add_job(
            self._collect_announcement,
            CronTrigger(minute="*/20"),
            id="collect_announcement_20min",
            name="公告增量采集",
            replace_existing=True,
        )

        self.scheduler.add_job(
            self._collect_sector,
            CronTrigger(hour="10-15", minute="30"),
            id="collect_sector_intraday",
            name="板块数据采集",
            replace_existing=True,
        )

        self.scheduler.add_job(
            self._collect_risk_events,
            CronTrigger(hour=6, minute=30),
            id="collect_risk_daily",
            name="风险事件采集",
            replace_existing=True,
        )

        self.scheduler.add_job(
            self._retry_failed_jobs,
            CronTrigger(minute="*/15"),
            id="retry_failed_jobs_15min",
            name="失败任务重试检查",
            replace_existing=True,
        )

        self.scheduler.add_job(
            self._save_watchlist_technical_analysis,
            CronTrigger(hour=10, minute=0),
            id="save_watchlist_technical_morning",
            name="关注股早盘技术研判保存",
            replace_existing=True,
        )
        self.scheduler.add_job(
            self._save_watchlist_technical_analysis,
            CronTrigger(hour=14, minute=30),
            id="save_watchlist_technical_afternoon",
            name="关注股收盘前技术研判保存",
            replace_existing=True,
        )

    def _collect_stock_basic(self):
        if self._is_weekend():
            logger.info("周末跳过: 股票基础信息同步")
            return
        logger.info("调度: 股票基础信息同步")
        self.service.create_and_run("STOCK_BASIC", trigger_type="SCHEDULED")

    def _collect_trade_status(self):
        if self._is_weekend():
            logger.info("周末跳过: 交易状态同步")
            return
        logger.info("调度: 交易状态同步")
        self.service.create_and_run("TRADE_STATUS", trigger_type="SCHEDULED")

    def _collect_quote(self):
        if self._is_weekend():
            logger.info("周末跳过: 延迟行情采集")
            return
        logger.info("调度: 延迟行情采集")
        self.service.create_and_run("QUOTE", trigger_type="SCHEDULED")

    def _collect_kline(self):
        if self._is_weekend():
            logger.info("周末跳过: 日 K 采集")
            return
        logger.info("调度: 日 K 采集")
        self.service.create_and_run("KLINE", trigger_type="SCHEDULED")

    def _collect_financial(self):
        if self._is_weekend():
            logger.info("周末跳过: 财务数据采集")
            return
        logger.info("调度: 财务数据采集")
        self.service.create_and_run("FINANCIAL", trigger_type="SCHEDULED")

    def _collect_announcement(self):
        logger.info("调度: 公告增量采集")
        self.service.create_and_run("ANNOUNCEMENT", trigger_type="SCHEDULED")

    def _collect_sector(self):
        if self._is_weekend():
            logger.info("周末跳过: 板块数据采集")
            return
        logger.info("调度: 板块数据采集")
        self.service.create_and_run("SECTOR", trigger_type="SCHEDULED")

    def _collect_risk_events(self):
        if self._is_weekend():
            logger.info("周末跳过: 风险事件采集")
            return
        logger.info("调度: 风险事件采集")
        self.service.create_and_run("RISK", trigger_type="SCHEDULED")

    def _retry_failed_jobs(self):
        logger.info("调度: 检查失败任务重试")
        self.service.retry_failed_jobs()

    def _save_watchlist_technical_analysis(self):
        if self._is_weekend():
            logger.info("周末跳过: 技术研判自动保存")
            return
        db = SessionLocal()
        try:
            rows = db.query(UserWatchlist).order_by(UserWatchlist.added_at.desc()).all()
            logger.info("调度: 自动保存关注股技术研判，共 %d 只", len(rows))
            for row in rows:
                try:
                    collect_stock(row.symbol, db)
                    logger.info("自动刷新关注股数据 [%s] 完成", row.symbol)
                    result = save_technical_analysis_for_symbol(db, row.symbol, allow_duplicate=False)
                    logger.info("自动保存技术研判 [%s] %s", row.symbol, result.get("analysisTimeLabel"))
                except Exception as exc:
                    logger.warning("自动保存技术研判 [%s] 失败: %s", row.symbol, exc)
        finally:
            db.close()
