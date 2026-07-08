import json
from decimal import Decimal
from statistics import median

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import AnnualReportExtraction, BusinessSegment, ExpenseItem, FinancialReport, KLineData, Stock, ValuationMetric
from backend.schemas.analysis import (
    AiInsight,
    DeepFundamentalAnalysis,
    DupontAnalysis,
    FundamentalModule,
    ImpactFactor,
    PeerComparisonItem,
    ScoreFactor,
    SegmentContributionItem,
    TechnicalIndicators,
    TrendBreakdownItem,
    ValuationPercentile,
    WatchSignal,
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


async def get_annual_report_extractions(session: AsyncSession, code: str) -> list[AnnualReportExtraction]:
    result = await session.execute(
        select(AnnualReportExtraction)
        .where(AnnualReportExtraction.code == code)
        .order_by(AnnualReportExtraction.report_period)
    )
    return list(result.scalars().all())


def serialize_annual_report_extraction(row: AnnualReportExtraction) -> dict[str, object]:
    data = {
        "code": row.code,
        "report_period": row.report_period,
        "document_id": row.document_id,
        "operating_profit": row.operating_profit,
        "total_profit": row.total_profit,
        "non_recurring_net_profit": row.non_recurring_net_profit,
        "income_tax_expense": row.income_tax_expense,
        "minority_interest": row.minority_interest,
        "other_income": row.other_income,
        "investment_income": row.investment_income,
        "fair_value_change_income": row.fair_value_change_income,
        "credit_impairment_loss": row.credit_impairment_loss,
        "asset_impairment_loss": row.asset_impairment_loss,
        "asset_disposal_income": row.asset_disposal_income,
        "cash_received_from_sales": row.cash_received_from_sales,
        "cash_received_other_operating": row.cash_received_other_operating,
        "inventory_total": row.inventory_total,
        "inventory_impairment": row.inventory_impairment,
        "capital_reserve": row.capital_reserve,
        "total_share_capital": row.total_share_capital,
        "rd_investment": row.rd_investment,
        "rd_investment_ratio": row.rd_investment_ratio,
        "patent_count": row.patent_count,
        "invention_patent_count": row.invention_patent_count,
        "construction_in_progress": row.construction_in_progress,
        "notes": _extraction_notes(row),
        "source": row.source,
        "review_status": row.review_status,
    }
    return data


async def calculate_deep_fundamental_analysis(
    session: AsyncSession, code: str
) -> DeepFundamentalAnalysis:
    reports = await get_financial_reports(session, code)
    valuations = await get_valuation_metrics(session, code)
    segments = await get_business_segments(session, code)
    expenses = await get_expense_items(session, code)
    extractions = await get_annual_report_extractions(session, code)
    stock = await _get_stock(session, code)
    peer_reports = await _get_peer_latest_reports(session, stock)

    trend_breakdown = _build_trend_breakdown(reports)
    dupont = _build_dupont_analysis(reports)
    peer_comparison = _build_peer_comparison(reports[-1] if reports else None, peer_reports)
    valuation_percentiles = _build_valuation_percentiles(valuations)
    score_factors = _build_score_factors(reports, trend_breakdown, peer_comparison, valuation_percentiles)
    segment_contribution = _build_segment_contribution(segments)
    impact_factors = _build_impact_factors(reports, expenses, segments)

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
        analysis_modules=_build_analysis_modules(
            reports, segment_contribution, impact_factors, valuation_percentiles, stock, extractions
        ),
        impact_factors=impact_factors,
        segment_contribution=segment_contribution,
        watch_signals=_build_watch_signals(reports, segment_contribution, impact_factors, valuation_percentiles),
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


def _build_segment_contribution(segments: list[BusinessSegment]) -> list[SegmentContributionItem]:
    latest_period = _latest_period([item.report_period for item in segments])
    latest_segments = [item for item in segments if item.report_period == latest_period]
    profit_total_by_type: dict[str, float] = {}
    for item in latest_segments:
        if item.gross_profit is not None:
            profit_total_by_type[item.segment_type] = profit_total_by_type.get(item.segment_type, 0.0) + float(item.gross_profit)

    output: list[SegmentContributionItem] = []
    for item in latest_segments:
        gross_profit = _to_float(item.gross_profit)
        total_profit = profit_total_by_type.get(item.segment_type)
        share = round(gross_profit / total_profit * 100, 2) if gross_profit is not None and total_profit else None
        output.append(
            SegmentContributionItem(
                report_period=item.report_period,
                segment_type=item.segment_type,
                segment_name=item.segment_name,
                revenue=_to_float(item.revenue),
                gross_profit=gross_profit,
                gross_margin=_to_float(item.gross_margin),
                revenue_yoy=_to_float(item.revenue_yoy),
                gross_profit_share=share,
                role=_segment_role(item.segment_type, share, _to_float(item.gross_margin)),
            )
        )
    return sorted(output, key=lambda item: item.gross_profit_share or 0, reverse=True)


def _build_impact_factors(
    reports: list[FinancialReport], expenses: list[ExpenseItem], segments: list[BusinessSegment]
) -> list[ImpactFactor]:
    if len(reports) < 2:
        return []
    latest = reports[-1]
    previous = reports[-2]
    latest_expense = _match_period_item(expenses, latest.report_period)
    previous_expense = _match_period_item(expenses, previous.report_period)
    latest_segments = [item for item in segments if item.report_period == latest.report_period]
    previous_segments = [item for item in segments if item.report_period == previous.report_period]

    revenue_delta = _delta(latest.revenue, previous.revenue)
    gross_profit_delta = _delta(latest.gross_profit, previous.gross_profit)
    net_profit_delta = _delta(latest.net_profit, previous.net_profit)
    factors = [
        _impact("收入规模变化", "业务增长", revenue_delta, "收入变化直接决定利润池规模"),
        _impact("毛利额变化", "毛利贡献", gross_profit_delta, "毛利额代表主营业务对利润的直接贡献"),
        _impact(
            "毛利率变化",
            "毛利贡献",
            _delta(latest.gross_margin, previous.gross_margin),
            "毛利率变化反映产品结构、价格和成本压力",
        ),
        _impact("净利润变化", "最终结果", net_profit_delta, "归母净利润是所有经营和非经常因素的综合结果"),
    ]
    if latest_expense and previous_expense:
        factors.extend(
            [
                _impact(
                    "销售费用变化",
                    "费用影响",
                    _neg_delta(latest_expense.selling_expense, previous_expense.selling_expense),
                    "费用增加会压低净利润，费用下降会释放利润",
                ),
                _impact(
                    "管理费用变化",
                    "费用影响",
                    _neg_delta(latest_expense.admin_expense, previous_expense.admin_expense),
                    "管理费用体现组织和运营成本变化",
                ),
                _impact(
                    "研发费用变化",
                    "技术投入",
                    _neg_delta(latest_expense.rd_expense, previous_expense.rd_expense),
                    "研发费用短期压低利润，长期支撑技术壁垒",
                ),
                _impact(
                    "财务费用变化",
                    "费用影响",
                    _neg_delta(latest_expense.finance_expense, previous_expense.finance_expense),
                    "财务费用体现利息、汇兑和资金成本影响",
                ),
            ]
        )
    factors.extend(_segment_impact_factors(latest_segments, previous_segments))
    return sorted(factors, key=lambda item: abs(item.impact or 0), reverse=True)


def _segment_impact_factors(
    latest_segments: list[BusinessSegment], previous_segments: list[BusinessSegment]
) -> list[ImpactFactor]:
    previous_by_key = {(item.segment_type, item.segment_name): item for item in previous_segments}
    factors: list[ImpactFactor] = []
    for item in latest_segments:
        previous = previous_by_key.get((item.segment_type, item.segment_name))
        if previous is None:
            continue
        factors.append(
            _impact(
                f"{item.segment_name}毛利额变化",
                "业务分部",
                _delta(item.gross_profit, previous.gross_profit),
                f"{item.segment_name}贡献变化用于判断主营业务结构是否改善",
            )
        )
    return factors


def _build_analysis_modules(
    reports: list[FinancialReport],
    segments: list[SegmentContributionItem],
    impacts: list[ImpactFactor],
    valuations: list[ValuationPercentile],
    stock: Stock | None,
    extractions: list[AnnualReportExtraction],
) -> list[FundamentalModule]:
    latest = reports[-1] if reports else None
    latest_extraction = _latest_extraction(extractions)
    top_segment = segments[0] if segments else None
    top_impacts = impacts[:3]
    valuation_text = "; ".join(f"{item.metric}{item.label}" for item in valuations[:2]) or "估值样本不足"
    industry = stock.industry_chain if stock and stock.industry_chain else "机器人产业链"
    return [
        FundamentalModule(
            title="产业逻辑入口",
            summary=f"从{industry}出发，先判断行业空间和国产替代逻辑，再回到公司兑现能力。",
            key_points=[
                f"核心产品：{stock.core_products}" if stock and stock.core_products else "需要补充核心产品标签",
                "重点跟踪机器人、精密传动和国产替代需求是否继续放量",
            ],
            status="positive" if latest and (latest.revenue or 0) > 0 else "neutral",
        ),
        FundamentalModule(
            title="公司业务结构",
            summary="按产品、行业、地区、销售模式拆开看，避免不同口径混加。",
            key_points=[
                f"最新主贡献：{top_segment.segment_name}，毛利占比{_format_percent(top_segment.gross_profit_share)}"
                if top_segment
                else "暂无业务分部数据",
                "产品口径用于判断利润来源，地区口径用于观察内外需结构",
            ],
            status="positive" if top_segment else "neutral",
        ),
        FundamentalModule(
            title="毛利与业务贡献拆解",
            summary="用收入、成本、毛利额和毛利率解释主营业务对利润变化的贡献。",
            key_points=[item.explanation for item in top_impacts if item.category in {"毛利贡献", "业务分部"}][:3]
            or ["需要更多分部毛利和成本数据"],
            status="positive" if any((item.impact or 0) > 0 for item in impacts if item.category == "毛利贡献") else "neutral",
        ),
        FundamentalModule(
            title="净利润影响因素排序",
            summary="将收入、毛利、费用和分部变化统一放入影响因素列表，按绝对影响额排序。",
            key_points=[f"{item.name}：{_format_money(item.impact)}，{item.explanation}" for item in top_impacts]
            or ["至少需要两期财报才能计算影响因素"],
            status="neutral",
        ),
        FundamentalModule(
            title="经营质量与现金流验证",
            summary=_cash_quality_summary(latest),
            key_points=["经营现金流需要持续匹配净利润", "若利润增长但现金流偏弱，需要核对应收、存货和回款"],
            status="positive" if latest and (_safe_ratio(latest.operating_cash_flow, latest.net_profit) or 0) >= 0.8 else "warning",
        ),
        FundamentalModule(
            title="资产负债与股本扩张潜力",
            summary=_leverage_summary(latest),
            key_points=[
                f"资本公积：{_format_money(_to_float(latest_extraction.capital_reserve))}" if latest_extraction else "资本公积待确认",
                f"股本：{_format_money(_to_float(latest_extraction.total_share_capital))}" if latest_extraction else "股本待确认",
                "结合募投项目和资本公积判断后续扩张潜力",
            ],
            status="neutral",
        ),
        FundamentalModule(
            title="技术护城河与产能兑现",
            summary="研发投入、专利、国家标准和产能项目共同构成技术壁垒证据链。",
            key_points=[
                f"研发费用率：{_format_percent(_to_float(latest.rd_ratio))}" if latest else "暂无研发费用率",
                f"研发投入：{_format_money(_to_float(latest_extraction.rd_investment))}" if latest_extraction else "研发投入待确认",
                f"专利/发明专利：{_format_count(latest_extraction.patent_count)} / {_format_count(latest_extraction.invention_patent_count)}" if latest_extraction else "专利数据待确认",
                _note_or_default(latest_extraction, "standards", "国家标准线索待确认"),
                _note_or_default(latest_extraction, "capacity_project", "产能项目线索待确认"),
            ],
            status="positive" if latest_extraction and (latest_extraction.rd_investment or latest_extraction.patent_count) else "neutral",
        ),
        FundamentalModule(
            title="市场定位与估值风险",
            summary=f"估值判断不单看便宜或贵，而要和增长兑现、市场定位一起看；当前{valuation_text}。",
            key_points=["高估值需要更强订单和利润兑现支撑", "低估值需要确认基本面是否已企稳"],
            status="warning" if any((item.percentile or 0) >= 70 for item in valuations) else "neutral",
        ),
    ]


def _build_watch_signals(
    reports: list[FinancialReport],
    segments: list[SegmentContributionItem],
    impacts: list[ImpactFactor],
    valuations: list[ValuationPercentile],
) -> list[WatchSignal]:
    latest = reports[-1] if reports else None
    top_segment = segments[0] if segments else None
    top_negative = next((item for item in impacts if item.direction == "negative"), None)
    pe = next((item for item in valuations if item.metric == "PE"), None)
    return [
        WatchSignal(
            name="收入与利润增速",
            value=f"收入{_format_money(_to_float(latest.revenue))} / 净利{_format_money(_to_float(latest.net_profit))}" if latest else "--",
            judgement="验证产业逻辑是否真正兑现到财报",
            source="财务报表",
        ),
        WatchSignal(
            name="主力业务毛利贡献",
            value=f"{top_segment.segment_name} {_format_percent(top_segment.gross_profit_share)}" if top_segment else "--",
            judgement="判断公司利润是否仍由核心业务驱动",
            source="业务分部",
        ),
        WatchSignal(
            name="最大负面因素",
            value=f"{top_negative.name} {_format_money(top_negative.impact)}" if top_negative else "暂无显著负面项",
            judgement="优先解释业绩下滑或利润弹性不足的来源",
            source="影响因素排序",
        ),
        WatchSignal(
            name="估值分位",
            value=f"PE {pe.label} / {_format_percent(pe.percentile)}" if pe else "--",
            judgement="判断市场预期是否已经透支",
            source="估值指标",
        ),
    ]


def _latest_extraction(extractions: list[AnnualReportExtraction]) -> AnnualReportExtraction | None:
    return sorted(extractions, key=lambda item: item.report_period)[-1] if extractions else None


def _extraction_notes(extraction: AnnualReportExtraction | None) -> dict[str, str]:
    if extraction is None or not extraction.notes_json:
        return {}
    try:
        data = json.loads(extraction.notes_json)
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _note_or_default(extraction: AnnualReportExtraction | None, key: str, default: str) -> str:
    return _extraction_notes(extraction).get(key) or default


def _format_count(value: Decimal | float | int | None) -> str:
    return "--" if value is None else f"{float(value):.0f}项"


def _impact(name: str, category: str, impact: float | None, explanation: str) -> ImpactFactor:
    if impact is None:
        direction = "neutral"
    elif impact > 0:
        direction = "positive"
    elif impact < 0:
        direction = "negative"
    else:
        direction = "neutral"
    return ImpactFactor(
        name=name,
        category=category,
        impact=round(impact, 2) if impact is not None else None,
        direction=direction,
        explanation=explanation,
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


def _delta(current: Decimal | float | int | None, previous: Decimal | float | int | None) -> float | None:
    if current is None or previous is None:
        return None
    return round(float(current) - float(previous), 2)


def _neg_delta(current: Decimal | float | int | None, previous: Decimal | float | int | None) -> float | None:
    value = _delta(current, previous)
    return -value if value is not None else None


def _latest_period(periods: list[str]) -> str | None:
    return sorted(periods)[-1] if periods else None


def _match_period_item(items: list[ExpenseItem], report_period: str) -> ExpenseItem | None:
    return next((item for item in items if item.report_period == report_period), None)


def _segment_role(segment_type: str, share: float | None, gross_margin: float | None) -> str:
    type_label = {
        "product": "产品口径",
        "industry": "行业口径",
        "region": "地区口径",
        "sales_mode": "销售模式口径",
    }.get(segment_type, "分部口径")
    if share is not None and share >= 50:
        return f"{type_label}核心利润来源"
    if gross_margin is not None and gross_margin >= 40:
        return f"{type_label}高毛利观察项"
    return f"{type_label}结构观察项"


def _cash_quality_summary(report: FinancialReport | None) -> str:
    if report is None:
        return "暂无财报数据，无法验证经营现金流质量。"
    match = _safe_ratio(report.operating_cash_flow, report.net_profit)
    if match is None:
        return "经营现金流或净利润缺失，需要补充现金流量表数据。"
    if match >= 1:
        return "经营现金流高于净利润，利润含金量较好。"
    if match >= 0.8:
        return "经营现金流基本匹配净利润，利润质量尚可。"
    return "经营现金流弱于净利润，需要核回应收、存货和回款压力。"


def _leverage_summary(report: FinancialReport | None) -> str:
    if report is None:
        return "暂无财报数据，无法判断资产负债结构。"
    multiplier = _safe_ratio(report.total_assets, report.net_assets)
    if multiplier is None:
        return "总资产或净资产缺失，需要补充资产负债表数据。"
    if multiplier <= 2:
        return "权益乘数较低，资产负债结构相对稳健。"
    if multiplier <= 4:
        return "权益乘数处于适中区间，需要跟踪扩张效率。"
    return "权益乘数偏高，需要警惕杠杆扩张风险。"


def _format_percent(value: float | None) -> str:
    return "--" if value is None else f"{value:.2f}%"


def _format_money(value: float | None) -> str:
    if value is None:
        return "--"
    abs_value = abs(value)
    sign = "-" if value < 0 else ""
    if abs_value >= 100000000:
        return f"{sign}{abs_value / 100000000:.2f}亿"
    if abs_value >= 10000:
        return f"{sign}{abs_value / 10000:.2f}万"
    return f"{value:.2f}"


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
