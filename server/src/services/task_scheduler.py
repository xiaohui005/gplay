import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.services.collection_service import CollectionService

logger = logging.getLogger(__name__)


class TaskScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.service = CollectionService()
        self._started = False

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

    def _collect_stock_basic(self):
        logger.info("调度: 股票基础信息同步")
        self.service.create_and_run("STOCK_BASIC", trigger_type="SCHEDULED")

    def _collect_trade_status(self):
        logger.info("调度: 交易状态同步")
        self.service.create_and_run("TRADE_STATUS", trigger_type="SCHEDULED")

    def _collect_quote(self):
        logger.info("调度: 延迟行情采集")
        self.service.create_and_run("QUOTE", trigger_type="SCHEDULED")

    def _collect_kline(self):
        logger.info("调度: 日 K 采集")
        self.service.create_and_run("KLINE", trigger_type="SCHEDULED")

    def _collect_financial(self):
        logger.info("调度: 财务数据采集")
        self.service.create_and_run("FINANCIAL", trigger_type="SCHEDULED")

    def _collect_announcement(self):
        logger.info("调度: 公告增量采集")
        self.service.create_and_run("ANNOUNCEMENT", trigger_type="SCHEDULED")

    def _collect_sector(self):
        logger.info("调度: 板块数据采集")
        self.service.create_and_run("SECTOR", trigger_type="SCHEDULED")

    def _collect_risk_events(self):
        logger.info("调度: 风险事件采集")
        self.service.create_and_run("RISK", trigger_type="SCHEDULED")

    def _retry_failed_jobs(self):
        logger.info("调度: 检查失败任务重试")
        self.service.retry_failed_jobs()
