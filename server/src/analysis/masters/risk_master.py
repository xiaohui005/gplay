from src.analysis.datatypes import RiskInput
from src.analysis.masters.base import (
    MASTER_BEARISH,
    MASTER_CAUTION,
    MASTER_INFO,
    MASTER_NEUTRAL,
    MasterConclusion,
)


def analyze_risk(risk: RiskInput, penalty: int) -> MasterConclusion:
    c = MasterConclusion(code="risk", name="风险大师")
    evidence: list[str] = []
    alerts: list[str] = []

    evidence.append(f"交易状态={risk.trade_status}")
    evidence.append(f"数据延迟={risk.delay_minutes}分钟")
    evidence.append(f"风险扣分={penalty}/100")

    if risk.trade_status == "DELISTED":
        c.status = MASTER_BEARISH
        c.explanation = "该股票已退市，风险极高，强烈建议回避。"
        c.detail = "股票已退市，不适用正常交易分析。"
        alerts.append("退市风险：该股票已正式退市")
    elif risk.trade_status == "SUSPENDED":
        c.status = MASTER_CAUTION
        c.explanation = "该股票当前停牌，请等待复牌。"
        c.detail = "股票停牌中，暂停交易，等待复牌后重新评估。"
        alerts.append("停牌提示：股票当前处于停牌状态")

    if risk.has_st_tag:
        alerts.append("ST 风险警示：该股票被实施特别处理")
        c.status = MASTER_BEARISH
        c.explanation = "ST 风险警示股票，建议回避。"
        c.detail = "ST/*ST 股票存在退市风险，基本面恶化，投资风险较高。"

    if risk.has_delist_risk:
        alerts.append("退市风险警示：存在退市风险")
        c.status = MASTER_BEARISH
        c.explanation = "存在退市风险，请高度警惕。"
        c.detail = "该股票已被实施退市风险警示（*ST），存在终止上市风险。"

    if risk.has_major_penalty:
        alerts.append("重大监管处罚：存在合规风险")
        c.status = MASTER_BEARISH
        c.explanation = "存在重大监管处罚，合规风险较高。"
        c.detail = "重大监管处罚会影响公司经营和股价，短期内不宜介入。"

    if risk.has_shareholder_reduction:
        alerts.append(f"股东减持风险")
        c.status = MASTER_CAUTION if c.status not in (MASTER_BEARISH,) else c.status
        c.explanation = "存在股东减持，对股价构成压力。" if not c.explanation else c.explanation + " 同时存在股东减持。"
        c.detail = "股东减持通常对短期股价构成压力，需关注减持进度和规模。"

    if risk.has_pledge_risk:
        alerts.append("质押风险：大股东质押比例较高")

    if risk.delay_minutes > 60:
        alerts.append(f"数据延迟 {risk.delay_minutes} 分钟，超过正常阈值")
        c.status = MASTER_CAUTION if c.status not in (MASTER_BEARISH,) else c.status

    if risk.data_missing:
        alerts.append("关键行情数据缺失，分析可靠性降低")
        c.status = MASTER_CAUTION if c.status not in (MASTER_BEARISH,) else c.status

    if not alerts:
        if penalty == 0:
            c.status = MASTER_INFO
            c.explanation = "当前未检测到明显风险信号。"
            c.detail = "交易状态正常，无 ST、退市、减持等风险事件。"
            alerts.append("暂无显著风险")
        elif penalty < 20:
            c.status = MASTER_INFO
            c.explanation = "存在轻微风险，整体可控。"
            c.detail = "风险扣分较低，主要是数据延迟等轻微因素。"
        else:
            c.status = MASTER_CAUTION
            c.explanation = f"存在多项风险因素（扣分 {penalty}），请注意防范。"
            c.detail = f"综合风控扣分 {penalty}，建议结合具体风险点审慎评估。"

    c.evidence = evidence + [f"风险大师：{'；'.join(alerts)}"]
    return c
