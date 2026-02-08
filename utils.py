"""
工具函数模块
"""
import csv
import os
from datetime import datetime
from typing import List
from database import db
from models import Trade
from config import EXPORTS_DIR


def export_to_csv() -> str:
    """导出交易记录到CSV文件"""
    trades = db.get_all_trades()

    filename = f"trades_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join(EXPORTS_DIR, filename)

    # 使用 utf-8-sig 编码，添加BOM头以支持Excel正确显示中文
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)

        # 写入表头
        writer.writerow([
            'ID', '交易日期', '交易所', '品种', '合约', '方向', '开仓价',
            '数量', '实物吨', '关联PO', '供应商', '结算价', '贴水',
            '止损价', '止盈价', '平仓价', '平仓日期', '手续费',
            '盈亏', '状态', 'MA5', 'MA10', 'MA20', 'RSI', 'MACD',
            '入场理由', '市场走势', '备注', '创建时间', '更新时间'
        ])

        # 写入数据
        for trade in trades:
            writer.writerow([
                trade.id, trade.trade_date, trade.exchange, trade.product_name,
                trade.contract, trade.direction, trade.entry_price, trade.quantity,
                trade.physical_tons, trade.related_po, trade.supplier,
                trade.settlement_price, trade.premium, trade.stop_loss, trade.take_profit,
                trade.exit_price, trade.exit_date, trade.fee, trade.profit_loss,
                trade.status, trade.ma5, trade.ma10, trade.ma20, trade.rsi, trade.macd,
                trade.entry_reason, trade.market_trend, trade.notes,
                trade.created_at, trade.updated_at
            ])

    return filepath


def import_from_csv(filepath: str) -> int:
    """从CSV文件导入交易记录"""
    count = 0
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            trade = Trade(
                trade_date=row.get('交易日期', ''),
                exchange=row.get('交易所', 'gfex'),
                product_name=row.get('品种', ''),
                contract=row.get('合约', ''),
                direction=row.get('方向', 'long'),
                entry_price=float(row.get('开仓价', 0)),
                quantity=float(row.get('数量', 0)),
                stop_loss=float(row['止损价']) if row.get('止损价') else None,
                take_profit=float(row['止盈价']) if row.get('止盈价') else None,
                exit_price=float(row['平仓价']) if row.get('平仓价') else None,
                exit_date=row.get('平仓日期') or None,
                fee=float(row.get('手续费', 0)),
                profit_loss=float(row.get('盈亏', 0)),
                status=row.get('状态', 'open'),
                ma5=float(row['MA5']) if row.get('MA5') else None,
                ma10=float(row['MA10']) if row.get('MA10') else None,
                ma20=float(row['MA20']) if row.get('MA20') else None,
                rsi=float(row['RSI']) if row.get('RSI') else None,
                macd=float(row['MACD']) if row.get('MACD') else None,
                entry_reason=row.get('入场理由') or None,
                market_trend=row.get('市场走势') or None,
                notes=row.get('备注') or None
            )
            db.create_trade(trade)
            count += 1

    return count


def format_currency(value: float) -> str:
    """格式化货币"""
    if value >= 0:
        return f"+¥{value:,.2f}"
    else:
        return f"-¥{abs(value):,.2f}"


def format_percentage(value: float) -> str:
    """格式化百分比"""
    return f"{value:.2f}%"


def get_color_for_value(value: float) -> str:
    """根据值返回颜色类"""
    if value > 0:
        return "text-green-600"
    elif value < 0:
        return "text-red-600"
    else:
        return "text-gray-600"
