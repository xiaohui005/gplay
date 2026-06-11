from dataclasses import dataclass, field


@dataclass
class MasterConclusion:
    code: str = ""
    name: str = ""
    status: str = "NEUTRAL"
    explanation: str = ""
    detail: str = ""
    evidence: list[str] = field(default_factory=list)


MASTER_BULLISH = "BULLISH"
MASTER_NEUTRAL = "NEUTRAL"
MASTER_BEARISH = "BEARISH"
MASTER_CAUTION = "CAUTION"
MASTER_INFO = "INFO"


def cond(cid: str, title: str, desc: str, evidence: str | list[str], status: str = "NOT_MET", importance: str = "MEDIUM") -> dict:
    if isinstance(evidence, str):
        evidence = [evidence]
    return {
        "conditionId": cid,
        "title": title,
        "description": desc,
        "evidence": evidence,
        "status": status,
        "importance": importance,
    }


def plan(title: str, price: str, comment: str, weight: int) -> dict:
    return {"title": title, "price": price, "comment": comment, "weight": weight}
