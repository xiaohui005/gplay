POSITIVE_KEYWORDS = [
    "涨停", "大涨", "暴涨", "拉升", "上攻", "突破", "创新高", "新高",
    "利好", "盈利", "预增", "扭亏", "净利润增长", "营收增长",
    "分红", "高送转", "增持", "回购", "中标", "签约", "战略合作",
    "订单", "产能", "扩张", "收购", "重组", "龙头", "领涨",
    "净买入", "净流入", "买入评级", "推荐", "关注", "机遇", "反弹",
    "放量", "触底", "企稳", "回升", "走强", "活跃",
]

NEGATIVE_KEYWORDS = [
    "跌停", "大跌", "暴跌", "跳水", "下挫", "下探",
    "利空", "亏损", "预亏", "净利润下滑", "营收下滑",
    "减持", "卖出", "净卖出", "净流出", "流出",
    "风险", "爆雷", "违约", "延期", "立案", "调查",
    "警示", "退市", "暂停上市", "停牌",
    "下跌", "回调", "抛售", "出货", "做空", "唱空", "看空",
    "熊市", "空头", "利差",
    "疲软", "低迷", "承压", "拖累", "打击", "困难",
]


def classify_sentiment(title: str, summary: str = "") -> str:
    text = title + " " + summary
    pos_score = 0
    neg_score = 0
    for kw in POSITIVE_KEYWORDS:
        if kw in text:
            pos_score += 1
    for kw in NEGATIVE_KEYWORDS:
        if kw in text:
            neg_score += 1
    if pos_score > neg_score:
        return "positive"
    if neg_score > pos_score:
        return "negative"
    return "neutral"
