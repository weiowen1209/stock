from decimal import Decimal

from backend.pdf_financial_parser import parse_financial_tables


SAMPLE_REPORT_TEXT = """
证券代码：688017
2024 年年度报告
报告期末：2024年12月31日
合并利润表
项目 2024年度 2023年度 单位：万元
营业总收入 123,456.78 100,000.00
二、营业总成本 95,000.00 82,000.00
其中：营业成本 83,456.78 70,000.00
销售费用 1,200.00 1,100.00
管理费用 2,300.00 2,100.00
研发费用 3,400.00 3,000.00
财务费用 -50.00 20.00
投资收益 2,000.00 1,000.00
资产减值损失 -300.00 -100.00
营业利润 18,000.00 14,000.00
1.归属于母公司股东的净利润
（净亏损以“-”号填列） 15,000.00 12,000.00
基本每股收益 1.23 0.98
合并资产负债表
项目 2024年12月31日 2023年12月31日 单位：万元
资产总计 500,000.00 450,000.00
归属于母公司所有者权益合计 280,000.00 240,000.00
合并现金流量表
经营活动产生的现金流量净额 18,000.00 14,000.00 单位：万元
销售商品、提供劳务收到的现金 120,000.00 99,000.00
资产负债表补充
资本公积 260,000.00 120,000.00 单位：万元
研发投入合计 3,500.00 单位：万元
研发投入占营业收入的比例 2.84
公司承担国家标准编制并推进年产50万台精密谐波减速器项目。
分产品
谐波减速器 90,000.00 50,000.00 44.44 20.00
机电一体化产品 33,456.78 33,456.78 0.00 10.00
分地区
境内 100,000.00 60,000.00 40.00 15.00
境外 23,456.78 23,456.78 0.00 5.00
"""


def test_parse_financial_tables_extracts_three_statement_fields():
    result = parse_financial_tables(SAMPLE_REPORT_TEXT)

    assert result.financial.code == "688017"
    assert result.financial.report_period == "2024年报"
    assert result.financial.report_date == "2024-12-31"
    assert result.financial.revenue == Decimal("1234567800.00")
    assert result.financial.gross_profit == Decimal("400000000.00")
    assert result.financial.gross_margin == Decimal("32.40")
    assert result.financial.net_profit == Decimal("150000000.00")
    assert result.financial.operating_cash_flow == Decimal("180000000.00")
    assert result.financial.total_assets == Decimal("5000000000.00")
    assert result.financial.net_assets == Decimal("2800000000.00")
    assert result.financial.eps == Decimal("1.23")
    assert result.financial.rd_ratio == Decimal("2.75")
    assert result.expenses is not None
    assert result.expenses.selling_expense == Decimal("12000000.00")
    assert result.expenses.admin_expense == Decimal("23000000.00")
    assert result.expenses.rd_expense == Decimal("34000000.00")
    assert result.expenses.finance_expense == Decimal("-500000.00")
    assert result.field_sources["revenue"]["section"] == "income"
    assert result.field_sources["total_assets"]["section"] == "balance"
    assert result.field_sources["operating_cash_flow"]["section"] == "cashflow"
    assert result.extractions is not None
    assert result.extractions.operating_profit == Decimal("180000000.00")
    assert result.extractions.investment_income == Decimal("20000000.00")
    assert result.extractions.asset_impairment_loss == Decimal("-3000000.00")
    assert result.extractions.cash_received_from_sales == Decimal("1200000000.00")
    assert result.extractions.capital_reserve == Decimal("2600000000.00")
    assert result.extractions.notes["standards"]
    assert [(item.segment_type, item.segment_name) for item in result.segments] == [
        ("product", "谐波减速器"),
        ("product", "机电一体化产品"),
        ("region", "境内"),
        ("region", "境外"),
    ]
    assert result.segments[0].revenue == Decimal("90000.00")
    assert result.segments[0].gross_margin == Decimal("44.44")


def test_parse_financial_tables_keeps_user_supplied_identity():
    result = parse_financial_tables(SAMPLE_REPORT_TEXT, code="300750", report_period="2024三季报")

    assert result.financial.code == "300750"
    assert result.financial.report_period == "2024三季报"
