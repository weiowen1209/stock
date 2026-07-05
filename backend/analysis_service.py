from decimal import Decimal
from statistics import median

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import BusinessSegment, ExpenseItem, FinancialReport, KLineData, Stock, ValuationMetric
from backend.schemas.analysis import (
    AiInsight,
    DeepFundamentalAnalysis,
    DupontAnalysis,
    PeerComparisonItem,
    ScoreFactor,
    TechnicalIndicators,
    TrendBreakdownItem,
    ValuationPercentile,
)


async def get_financial_reports(session: AsyncSession, code: str) -> list[FinancialReport]:
    result = await session.execute(
        select(FinancialReport)
        .where(FinancialReport.code == code)
        .order_by(FinancialReport.report_date, FinancialReport.report_period)
    )
    return list(result.scalars().all())


async def get_business_segments(session: AsyncSession, code: str) -> list[BusinessSegment]:
    result = await session.execute(
        select(BusinessSegment)
        .where(BusinessSegment.code == code)
        .order_by(BusinessSegment.report_period, BusinessSegment.segment_type, BusinessSegment.segment_name)
    )
    return list(result.scalars().all())


async def get_expense_items(session: AsyncSession, code: str) -> list[ExpenseItem]:
    result = await session.execute(
        select(ExpenseItem).where(ExpenseItem.code == code).order_by(ExpenseItem.report_period)
    )
    return list(result.scalars().all())


async def get_valuation_metrics(session: AsyncSession, code: str) -> list[ValuationMetric]:
    result = await session.execute(
        select(ValuationMetric).where(ValuationMetric.code == code).order_by(ValuationMetric.date)
    )
    return list(result.scalars().all())


async def calculate_deep_fundamental_analysis(
    session: AsyncSession, code: str
) -> DeepFundamentalAnalysis:
    reports = await get_financial_reports(session, code)
    valuations = await get_valuation_metrics(session, code)
    stock = await _get_stock(session, code)
    peer_reports = await _get_peer_latest_reports(session, stock)

    trend_breakdown = _build_trend_breakdown(reports)
    dupont = _build_dupont_analysis(reports)
    peer_comparison = _build_peer_comparison(reports[-1] if reports else None, peer_reports)
    valuation_percentiles = _build_valuation_percentiles(valuations)
    score_factors = _build_score_factors(reports, trend_breakdown, peer_comparison, valuation_percentiles)

    quality_score = _weighted_score(score_factors, {"profitability", "cash", "leverage"})
    growth_score = _weighted_score(score_factors, {"growth", "margin_trend", "peer_growth"})
    valuation_score = _weighted_score(score_factors, {"valuation"})
    overall_score = _weighted_score(score_factors, {factor.name for factor in score_factors})

    return DeepFundamentalAnalysis(
        code=code,
        report_period=reports[-1].report_period if reports else None,
        overall_score=overall_score,
        growth_potential_score=growth_score,
        quality_score=quality_score,
        valuation_score=valuation_score,
        score_factors=score_factors,
        trend_breakdown=trend_breakdown,
        dupont=dupont,
        peer_comparison=peer_comparison,
        valuation_percentiles=valuation_percentiles,
        ai_insight=_build_ai_insight(overall_score, growth_score, quality_score, valuation_score, score_factors),
    )


async def calculate_technical_indicators(
    session: AsyncSession, code: str, period: str = "day"
) -> TechnicalIndicators:
    result = await session.execute(
        select(KLineData).where(KLineData.code == code, KLineData.period == period).order_by(KLineData.date)
    )
    rows = list(result.scalars().all())
    closes = [float(row.close or 0) for row in rows]
    return TechnicalIndicators(
        code=code,
        period=period,
        dates=[row.date for row in rows],
        close=closes,
        ma5=_moving_average(closes, 5),
        ma10=_moving_average(closes, 10),
        ma20=_moving_average(closes, 20),
        **_macd(closes),
        rsi6=_rsi(closes, 6),
    )


async def _get_stock(session: AsyncSession, code: str) -> Stock | None:
    result = await session.execute(select(Stock).where(Stock.code == code))
    return result.scalar_one_or_none()


async def _get_peer_latest_reports(session: AsyncSession, stock: Stock | None) -> list[FinancialReport]:
    if stock is None:
        return []
    stock_result = await session.execute(
        select(Stock.code).where(Stock.industry_chain == stock.industry_chain, Stock.code != stock.code)
    )
    peer_codes = list(stock_result.scalars().all())
    if not peer_codes:
        return []
    report_result = await session.execute(select(FinancialReport).where(FinancialReport.code.in_(peer_codes)))
    latest_by_code: dict[str, FinancialReport] = {}
    for report in report_result.scalars().all():
        current = latest_by_code.get(report.code)
        report_key = str(report.report_date or report.report_period)
        current_key = str(current.report_date or current.report_period) if current else ""
        if current is None or report_key > current_key:
            latest_by_code[report.code] = report
    return list(latest_by_code.values())


def _build_trend_breakdown(reports: list[FinancialReport]) -> list[TrendBreakdownItem]:
    output: list[TrendBreakdownItem] = []
    annual_reports = [report for report in reports if "年报" in report.report_period]
    for index, report in enumerate(reports):
        previous = reports[index - 1] if index > 0 else None
        prior_year = _find_prior_year_report(report, annual_reports)
        revenue_yoy = _growth_rate(report.revenue, prior_year.revenue if prior_year else None)
        net_profit_yoy = _growth_rate(report.net_profit, prior_year.net_profit if prior_year else None)
        revenue_qoq = _growth_rate(report.revenue, previous.revenue if previous else None)
        net_profit_qoq = _growth_rate(report.net_profit, previous.net_profit if previous else None)
        output.append(
            TrendBreakdownItem(
                report_period=report.report_period,
                revenue_yoy=revenue_yoy,
                revenue_qoq=revenue_qoq,
                net_profit_yoy=net_profit_yoy,
                net_profit_qoq=net_profit_qoq,
                gross_margin_change=_difference(report.gross_margin, previous.gross_margin if previous else None),
                cash_flow_match=_safe_ratio(report.operating_cash_flow, report.net_profit),
                revenue_growth_contribution=_growth_contribution(report.revenue, previous.revenue if previous else None),
                net_profit_growth_contribution=_growth_contribution(report.net_profit, previous.net_profit if previous else None),
                signal=_trend_signal(revenue_yoy, net_profit_yoy, _safe_ratio(report.operating_cash_flow, report.net_profit)),
            )
        )
    return output


def _build_dupont_analysis(reports: list[FinancialReport]) -> list[DupontAnalysis]:
    output: list[DupontAnalysis] = []
    for report in reports:
        net_margin = _safe_ratio(report.net_profit, report.revenue)
        asset_turnover = _safe_ratio(report.revenue, report.total_assets)
        equity_multiplier = _safe_ratio(report.total_assets, report.net_assets)
        roe_estimated = _dupont_roe(net_margin, asset_turnover, equity_multiplier)
        driver = _dupont_driver(net_margin, asset_turnover, equity_multiplier)
        output.append(
            DupontAnalysis(
                report_period=report.report_period,
                roe=_to_float(report.roe),
                net_margin=net_margin,
                asset_turnover=asset_turnover,
                equity_multiplier=equity_multiplier,
                roe_estimated=roe_estimated,
                primary_driver=driver,
                interpretation=_dupont_interpretation(driver, net_margin, asset_turnover, equity_multiplier),
            )
        )
    return output


def _build_peer_comparison(
    latest: FinancialReport | None, peer_reports: list[FinancialReport]
) -> list[PeerComparisonItem]:
    if latest is None:
        return []
    metrics = [
        ("收入规模", _to_float(latest.revenue), [_to_float(item.revenue) for item in peer_reports]),
        ("净利率", _safe_ratio(latest.net_profit, latest.revenue), [_safe_ratio(item.net_profit, item.revenue) for item in peer_reports]),
        ("ROE", _to_float(latest.roe), [_to_float(item.roe) for item in peer_reports]),
        ("研发费用率", _to_float(latest.rd_ratio), [_to_float(item.rd_ratio) for item in peer_reports]),
    ]
    return [
        PeerComparisonItem(
            metric=name,
            company_value=value,
            peer_median=_median(peer_values),
            percentile=_percentile(value, peer_values),
            conclusion=_peer_conclusion(value, _median(peer_values)),
        )
        for name, value, peer_values in metrics
    ]


def _build_valuation_percentiles(valuations: list[ValuationMetric]) -> list[ValuationPercentile]:
    latest = valuations[-1] if valuations else None
    metrics = [
        ("PE", _to_float(latest.pe) if latest else None, [_to_float(item.pe) for item in valuations]),
        ("PB", _to_float(latest.pb) if latest else None, [_to_float(item.pb) for item in valuations]),
        ("PEG", _to_float(latest.peg) if latest else None, [_to_float(item.peg) for item in valuations]),
    ]
    output: list[ValuationPercentile] = []
    for name, value, values in metrics:
        percentile = _percentile(value, values)
        valid_values = [item for item in values if item is not None]
        output.append(
            ValuationPercentile(
                metric=name,
                current=value,
                percentile=percentile,
                label=_valuation_label(percentile),
                comment=_valuation_comment(name, percentile),
                sample_size=len(valid_values),
                upside_room=_valuation_upside_room(value, valid_values),
            )
        )
    return output


def _build_score_factors(
    reports: list[FinancialReport],
    trend: list[TrendBreakdownItem],
    peers: list[PeerComparisonItem],
    valuations: list[ValuationPercentile],
) -> list[ScoreFactor]:
    latest = reports[-1] if reports else None
    latest_trend = trend[-1] if trend else None
    latest_dupont = _build_dupont_analysis([latest])[0] if latest else None
    pe_percentile = next((item.percentile for item in valuations if item.metric == "PE"), None)
    peer_roe = next((item.percentile for item in peers if item.metric == "ROE"), None)
    return [
        _score_factor(
            name="growth",
            score=_score_growth(latest_trend),
            weight=0.22,
            value=latest_trend.revenue_yoy if latest_trend else None,
            benchmark="收入与利润增速",
            comment="增速越稳定，增长潜力越强",
            direction="higher_better",
        ),
        _score_factor(
            name="margin_trend",
            score=_score_margin(latest_trend),
            weight=0.14,
            value=latest_trend.gross_margin_change if latest_trend else None,
            benchmark="毛利率趋势",
            comment="毛利率稳定说明增长质量更好",
            direction="higher_better",
        ),
        _score_factor(
            name="cash",
            score=_score_cash(latest_trend),
            weight=0.16,
            value=latest_trend.cash_flow_match if latest_trend else None,
            benchmark="现金流匹配",
            comment="经营现金流应接近或高于净利润",
            direction="higher_better",
        ),
        _score_factor(
            name="profitability",
            score=_score_positive(latest_dupont.net_margin if latest_dupont else None, 0.15),
            weight=0.16,
            value=latest_dupont.net_margin if latest_dupont else None,
            benchmark="净利率",
            comment="利润率决定增长含金量",
            direction="higher_better",
        ),
        _score_factor(
            name="leverage",
            score=_score_leverage(latest_dupont.equity_multiplier if latest_dupont else None),
            weight=0.10,
            value=latest_dupont.equity_multiplier if latest_dupont else None,
            benchmark="权益乘数",
            comment="过高杠杆会削弱增长安全性",
            direction="lower_moderate_better",
        ),
        _score_factor(
            name="peer_growth",
            score=_score_percentile(peer_roe),
            weight=0.10,
            value=peer_roe,
            benchmark="行业分位",
            comment="高于同业说明兑现能力更强",
            direction="higher_better",
        ),
        _score_factor(
            name="valuation",
            score=_score_valuation(pe_percentile),
            weight=0.12,
            value=pe_percentile,
            benchmark="估值分位",
            comment="估值越低，未来重估空间越充分",
            direction="lower_better",
        ),
    ]


def _score_factor(
    name: str,
    score: float,
    weight: float,
    value: float | None,
    benchmark: str,
    comment: str,
    direction: str,
) -> ScoreFactor:
    return ScoreFactor(
        name=name,
        score=round(score, 2),
        weight=weight,
        value=value,
        benchmark=benchmark,
        comment=comment,
        level=_score_level(score),
        direction=direction,
    )


def _build_ai_insight(
    overall: float, growth: float, quality: float, valuation: float, factors: list[ScoreFactor]
) -> AiInsight:
    positives = [factor.comment for factor in factors if factor.score >= 70][:3]
    risks = [factor.comment for factor in factors if factor.score < 50][:3]
    conclusion = "增长潜力较强" if overall >= 70 else "增长潜力中等" if overall >= 50 else "增长潜力偏弱"
    if growth >= 70 and valuation < 50:
        conclusion += "，但估值已反映较多乐观预期"
    return AiInsight(
        conclusion=conclusion,
        positives=positives or ["暂无足够强项，需要补充更多财务与行业数据"],
        risks=risks or ["暂未发现显著短板，但仍需跟踪后续财报兑现"],
        watch_items=[
            "收入增速能否持续高于行业",
            "经营现金流是否继续匹配净利润",
            "估值分位是否继续上行并透支增长预期",
        ],
    )


def _weighted_score(factors: list[ScoreFactor], names: set[str]) -> float:
    selected = [factor for factor in factors if factor.name in names]
    total_weight = sum(factor.weight for factor in selected)
    if total_weight == 0:
        return 0.0
    return round(sum(factor.score * factor.weight for factor in selected) / total_weight, 2)


def _to_float(value: Decimal | float | int | None) -> float | None:
    return float(value) if value is not None else None


def _safe_ratio(numerator: Decimal | float | int | None, denominator: Decimal | float | int | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    denominator_float = float(denominator)
    if denominator_float == 0:
        return None
    return round(float(numerator) / denominator_float, 4)


def _find_prior_year_report(report: FinancialReport, reports: list[FinancialReport]) -> FinancialReport | None:
    if report.report_date is None:
        return None
    target_year = report.report_date.year - 1
    candidates = [item for item in reports if item.report_date and item.report_date.year == target_year]
    return candidates[-1] if candidates else None


def _growth_contribution(current: Decimal | None, previous: Decimal | None) -> float | None:
    if current is None or previous is None:
        return None
    delta = float(current - previous)
    base = abs(float(previous))
    if base == 0:
        return None
    return round(delta / base * 100, 2)


def _trend_signal(revenue_yoy: float | None, profit_yoy: float | None, cash_match: float | None) -> str:
    if revenue_yoy is None and profit_yoy is None:
        return "样本不足"
    if (revenue_yoy or 0) > 15 and (profit_yoy or 0) > 15 and (cash_match or 0) >= 0.8:
        return "高质量增长"
    if (revenue_yoy or 0) > 10 and (profit_yoy or 0) <= 0:
        return "增收不增利"
    if (revenue_yoy or 0) < 0 or (profit_yoy or 0) < 0:
        return "增长承压"
    if cash_match is not None and cash_match < 0.5:
        return "现金流偏弱"
    return "稳健增长"


def _growth_rate(current: Decimal | None, previous: Decimal | None) -> float | None:
    ratio = _safe_ratio(current - previous if current is not None and previous is not None else None, previous)
    return round(ratio * 100, 2) if ratio is not None else None


def _difference(current: Decimal | None, previous: Decimal | None) -> float | None:
    if current is None or previous is None:
        return None
    return round(float(current - previous), 2)


def _median(values: list[float | None]) -> float | None:
    valid = [value for value in values if value is not None]
    return round(float(median(valid)), 4) if valid else None


def _percentile(value: float | None, values: list[float | None]) -> float | None:
    valid = sorted(item for item in values if item is not None)
    if value is None or not valid:
        return None
    below_or_equal = sum(1 for item in valid if item <= value)
    return round(below_or_equal / len(valid) * 100, 2)


def _valuation_upside_room(value: float | None, values: list[float]) -> float | None:
    if value is None or not values:
        return None
    center = median(values)
    if value == 0:
        return None
    return round((center - value) / value * 100, 2)


def _dupont_roe(net_margin: float | None, asset_turnover: float | None, equity_multiplier: float | None) -> float | None:
    if net_margin is None or asset_turnover is None or equity_multiplier is None:
        return None
    return round(net_margin * asset_turnover * equity_multiplier * 100, 2)


def _dupont_interpretation(
    driver: str, net_margin: float | None, asset_turnover: float | None, equity_multiplier: float | None
) -> str:
    if driver == "数据不足":
        return "关键财务字段不足，暂无法拆解 ROE 来源"
    if driver == "净利率":
        return "ROE 主要受盈利能力驱动，需关注毛利率和费用率变化"
    if driver == "资产周转率":
        return "ROE 主要受运营效率驱动，需关注收入增长和资产利用效率"
    if equity_multiplier is not None and equity_multiplier > 4:
        return "ROE 对杠杆依赖较高，需关注负债扩张风险"
    return "ROE 结构较均衡，需持续观察利润率、周转率和杠杆变化"


def _score_level(score: float) -> str:
    if score >= 80:
        return "优秀"
    if score >= 65:
        return "良好"
    if score >= 50:
        return "中性"
    return "偏弱"


def _peer_conclusion(value: float | None, peer_median: float | None) -> str:
    if value is None or peer_median is None:
        return "同业样本不足"
    if value > peer_median:
        return "高于同业中位数"
    if value < peer_median:
        return "低于同业中位数"
    return "接近同业中位数"


def _valuation_label(percentile: float | None) -> str:
    if percentile is None:
        return "样本不足"
    if percentile >= 70:
        return "偏高"
    if percentile <= 30:
        return "偏低"
    return "中性"


def _valuation_comment(metric: str, percentile: float | None) -> str:
    if percentile is None:
        return f"{metric} 历史样本不足，暂不判断"
    if percentile >= 70:
        return f"{metric} 处于偏高分位，需警惕预期透支"
    if percentile <= 30:
        return f"{metric} 处于偏低分位，存在重估空间"
    return f"{metric} 处于中性分位，需结合增长兑现判断"


def _dupont_driver(net_margin: float | None, asset_turnover: float | None, equity_multiplier: float | None) -> str:
    values = {
        "净利率": net_margin,
        "资产周转率": asset_turnover,
        "权益乘数": equity_multiplier if equity_multiplier is not None and equity_multiplier > 3 else None,
    }
    valid = {key: value for key, value in values.items() if value is not None}
    if not valid:
        return "数据不足"
    return max(valid, key=lambda key: valid[key] or 0)


def _score_growth(trend: TrendBreakdownItem | None) -> float:
    if trend is None or trend.revenue_yoy is None:
        return 45.0
    profit = trend.net_profit_yoy if trend.net_profit_yoy is not None else trend.revenue_yoy
    return max(0.0, min(100.0, 50 + trend.revenue_yoy * 1.2 + profit * 0.8))


def _score_margin(trend: TrendBreakdownItem | None) -> float:
    if trend is None or trend.gross_margin_change is None:
        return 50.0
    return max(0.0, min(100.0, 60 + trend.gross_margin_change * 4))


def _score_cash(trend: TrendBreakdownItem | None) -> float:
    if trend is None or trend.cash_flow_match is None:
        return 45.0
    return max(0.0, min(100.0, trend.cash_flow_match * 70))


def _score_positive(value: float | None, target: float) -> float:
    if value is None:
        return 45.0
    return max(0.0, min(100.0, value / target * 80))


def _score_leverage(value: float | None) -> float:
    if value is None:
        return 55.0
    if value <= 2:
        return 85.0
    if value <= 4:
        return 65.0
    return 35.0


def _score_percentile(value: float | None) -> float:
    return value if value is not None else 45.0


def _score_valuation(percentile: float | None) -> float:
    if percentile is None:
        return 50.0
    return max(0.0, min(100.0, 100 - percentile))


def _moving_average(values: list[float], window: int) -> list[float | None]:
    output: list[float | None] = []
    for index in range(len(values)):
        if index + 1 < window:
            output.append(None)
            continue
        chunk = values[index + 1 - window : index + 1]
        output.append(round(sum(chunk) / window, 4))
    return output


def _ema(values: list[float], span: int) -> list[float]:
    if not values:
        return []
    alpha = 2 / (span + 1)
    output = [values[0]]
    for value in values[1:]:
        output.append(alpha * value + (1 - alpha) * output[-1])
    return output


def _macd(values: list[float]) -> dict[str, list[float | None]]:
    if not values:
        return {"macd": [], "signal": [], "histogram": []}
    ema12 = _ema(values, 12)
    ema26 = _ema(values, 26)
    dif = [short - long for short, long in zip(ema12, ema26)]
    dea = _ema(dif, 9)
    histogram = [(d - s) * 2 for d, s in zip(dif, dea)]
    return {
        "macd": [round(item, 4) for item in dif],
        "signal": [round(item, 4) for item in dea],
        "histogram": [round(item, 4) for item in histogram],
    }


def _rsi(values: list[float], window: int) -> list[float | None]:
    output: list[float | None] = [None]
    for index in range(1, len(values)):
        if index < window:
            output.append(None)
            continue
        gains = []
        losses = []
        for left, right in zip(values[index + 1 - window : index], values[index + 2 - window : index + 1]):
            change = right - left
            if change >= 0:
                gains.append(change)
            else:
                losses.append(abs(change))
        avg_gain = sum(gains) / window
        avg_loss = sum(losses) / window
        if avg_loss == 0:
            output.append(100.0)
        else:
            rs = avg_gain / avg_loss
            output.append(round(100 - 100 / (1 + rs), 4))
    return output


def decimal_or_none(value: float | int | str | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))
