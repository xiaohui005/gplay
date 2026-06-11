from src.analysis.datatypes import (
    CapitalInput,
    EventInput,
    FinancialInput,
    KlineInput,
    QuoteInput,
    RiskInput,
    SectorInput,
)


def score_trend(kline: KlineInput, quote: QuoteInput | None = None) -> int:
    base = 50
    has_ma = False

    if kline.ma5 is not None and kline.ma10 is not None and kline.ma20 is not None:
        has_ma = True
        above_ma5 = quote is not None and quote.latest_price is not None and quote.latest_price >= kline.ma5
        above_ma10 = quote is not None and quote.latest_price is not None and quote.latest_price >= kline.ma10
        above_ma20 = quote is not None and quote.latest_price is not None and quote.latest_price >= kline.ma20
        above_ma60 = kline.ma60 is not None and quote is not None and quote.latest_price is not None and quote.latest_price >= kline.ma60

        if above_ma5:
            base += 10
        if above_ma10:
            base += 10
        if above_ma20:
            base += 10

        if kline.ma5 > kline.ma10 > kline.ma20:
            base += 15

        if kline.ma60 is not None and not above_ma60:
            base -= 10
        if not above_ma20:
            base -= 10

    if quote is not None and quote.change_percent is not None:
        cp = quote.change_percent
        if cp >= 5:
            base += 10
        elif cp >= 3:
            base += 5
        elif cp <= -5:
            base -= 10
        elif cp <= -3:
            base -= 5

    if not has_ma:
        base = 50

    return max(0, min(100, base))


def score_volume_price(quote: QuoteInput | None = None) -> int:
    if quote is None:
        return 50
    base = 50
    vr = quote.volume_ratio
    cp = quote.change_percent

    if vr is not None and cp is not None:
        if vr >= 1.5 and cp >= 3:
            base += 20
        elif vr >= 1.3 and cp >= 2:
            base += 10
        elif vr <= 0.7 and -1 <= cp <= 0:
            base += 10

        if vr >= 1.5 and cp < 0.5:
            base -= 20
        elif vr <= 0.5 and cp >= 3:
            base -= 15
        elif vr >= 2.0 and cp < 1.0:
            base -= 10

    if vr is not None and vr > 1.0:
        base += 5
    elif vr is not None and vr < 0.5:
        base -= 5

    return max(0, min(100, base))


def score_capital(capital: CapitalInput | None = None) -> int:
    if capital is None:
        return 50
    base = 50

    if capital.main_net_inflow is not None:
        if capital.main_net_inflow > 0:
            base += 15
        elif capital.main_net_inflow < 0:
            base -= 15

    if capital.main_net_inflow_3d is not None:
        if capital.main_net_inflow_3d > 0:
            base += 10
        elif capital.main_net_inflow_3d < 0:
            base -= 10

    return max(0, min(100, base))


def score_sector(sector: SectorInput | None = None) -> int:
    if sector is None:
        return 50
    base = 50

    if sector.sector_change_pct is not None:
        if sector.sector_change_pct > 2:
            base += 15
        elif sector.sector_change_pct > 0:
            base += 5
        elif sector.sector_change_pct < -2:
            base -= 15
        elif sector.sector_change_pct < 0:
            base -= 5

    if sector.sector_rank is not None:
        if sector.sector_rank <= 10:
            base += 10
        elif sector.sector_rank <= 30:
            base += 5
        elif sector.sector_rank >= 80:
            base -= 10

    return max(0, min(100, base))


def score_fundamental(financial: FinancialInput | None = None) -> int:
    if financial is None:
        return 50
    base = 50

    if financial.roe is not None:
        if financial.roe > 15:
            base += 15
        elif financial.roe > 10:
            base += 10
        elif financial.roe > 5:
            base += 5
        elif financial.roe < 0:
            base -= 15

    if financial.pe is not None:
        pf = abs(financial.pe)
        if 0 < pf <= 15:
            base += 10
        elif pf > 50:
            base -= 10
        elif pf > 100:
            base -= 15

    if financial.profit_change_pct is not None:
        if financial.profit_change_pct > 20:
            base += 10
        elif financial.profit_change_pct > 0:
            base += 5
        elif financial.profit_change_pct < -20:
            base -= 15
        elif financial.profit_change_pct < 0:
            base -= 5

    return max(0, min(100, base))


def score_event(event: EventInput | None = None) -> int:
    if event is None:
        return 50
    base = 50

    if event.has_positive_news:
        base += 15
    if event.has_negative_news:
        base -= 15
    if event.has_regulatory_penalty:
        base -= 25
    if event.has_shareholder_reduction:
        base -= 10

    return max(0, min(100, base))


def compute_risk_penalty(risk: RiskInput) -> int:
    penalty = 0

    if risk.trade_status == "DELISTED":
        penalty += 100
    elif risk.trade_status == "SUSPENDED":
        penalty += 60

    if risk.has_st_tag:
        penalty += 40
    if risk.has_delist_risk:
        penalty += 50
    if risk.has_major_penalty:
        penalty += 50
    if risk.has_shareholder_reduction:
        penalty += 20
    if risk.has_pledge_risk:
        penalty += 15

    if risk.delay_minutes > 60:
        penalty += 15
    elif risk.delay_minutes > 30:
        penalty += 5

    if risk.data_missing:
        penalty += 30

    return min(100, penalty)
