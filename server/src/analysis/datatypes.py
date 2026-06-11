from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class QuoteInput:
    latest_price: float | None = None
    change_percent: float | None = None
    volume: float | None = None
    amount: float | None = None
    turnover_rate: float | None = None
    volume_ratio: float | None = None
    high: float | None = None
    low: float | None = None
    open_price: float | None = None
    pre_close: float | None = None
    amplitude: float | None = None
    data_time: datetime | None = None
    delay_minutes: int = 0


@dataclass
class KlineInput:
    ma5: float | None = None
    ma10: float | None = None
    ma20: float | None = None
    ma60: float | None = None


@dataclass
class CapitalInput:
    main_net_inflow: float | None = None
    main_net_inflow_3d: float | None = None


@dataclass
class FinancialInput:
    pe: float | None = None
    pb: float | None = None
    roe: float | None = None
    profit_change_pct: float | None = None


@dataclass
class SectorInput:
    sector_name: str | None = None
    sector_change_pct: float | None = None
    sector_rank: int | None = None


@dataclass
class EventInput:
    has_positive_news: bool = False
    has_negative_news: bool = False
    has_regulatory_penalty: bool = False
    has_shareholder_reduction: bool = False


@dataclass
class RiskInput:
    trade_status: str = "TRADING"
    has_st_tag: bool = False
    has_delist_risk: bool = False
    has_major_penalty: bool = False
    has_shareholder_reduction: bool = False
    has_pledge_risk: bool = False
    delay_minutes: int = 0
    data_missing: bool = False


@dataclass
class StrategyWeights:
    trend: float = 25.0
    volume_price: float = 20.0
    capital: float = 20.0
    sector: float = 15.0
    fundamental: float = 10.0
    event: float = 10.0


DEFAULT_WEIGHTS = StrategyWeights()
DISCLAIMER = "仅供参考，不构成任何投资建议或收益承诺。投资有风险，入市需谨慎。"
