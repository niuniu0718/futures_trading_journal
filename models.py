"""
数据模型定义
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Trade:
    """交易记录模型"""
    id: Optional[int] = None
    trade_date: str = None
    exchange: str = 'gfex'
    product_name: str = ''
    contract: str = ''
    direction: str = 'long'
    entry_price: float = 0.0
    quantity: float = 0.0
    supplier: Optional[str] = None  # 供应商
    settlement_price: Optional[float] = None  # 结算价格
    premium: Optional[float] = None  # 贴水
    physical_tons: Optional[float] = None  # 实物吨（自动计算：quantity × 1.13）
    related_po: Optional[str] = None  # 关联PO
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    exit_price: Optional[float] = None
    exit_date: Optional[str] = None
    fee: float = 0.0
    profit_loss: float = 0.0
    status: str = 'open'
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    rsi: Optional[float] = None
    macd: Optional[float] = None
    entry_reason: Optional[str] = None
    market_trend: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        """初始化后处理"""
        if self.created_at is None:
            self.created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if self.updated_at is None:
            self.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    @property
    def exchange_name(self):
        """获取交易所中文名称"""
        from config import EXCHANGES
        return EXCHANGES.get(self.exchange, self.exchange)

    @property
    def direction_name(self):
        """获取方向中文名称"""
        from config import DIRECTIONS
        return DIRECTIONS.get(self.direction, self.direction)

    @property
    def status_name(self):
        """获取状态中文名称"""
        from config import STATUSES
        return STATUSES.get(self.status, self.status)

    @property
    def trend_name(self):
        """获取走势中文名称"""
        from config import TRENDS
        return TRENDS.get(self.market_trend, self.market_trend or '-')

    def calculate_profit_loss(self):
        """
        计算盈亏
        期货盈亏计算公式:
        多单: (平仓价 - 开仓价) * 合约乘数 * 手数
        空单: (开仓价 - 平仓价) * 合约乘数 * 手数
        这里简化为直接使用价格差 * 数量
        """
        if self.exit_price and self.exit_price > 0:
            if self.direction == 'long':
                gross_profit = (self.exit_price - self.entry_price) * self.quantity
            else:  # short
                gross_profit = (self.entry_price - self.exit_price) * self.quantity
            self.profit_loss = gross_profit - self.fee
        else:
            self.profit_loss = 0.0
        return self.profit_loss

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'trade_date': self.trade_date,
            'exchange': self.exchange,
            'exchange_name': self.exchange_name,
            'product_name': self.product_name,
            'contract': self.contract,
            'direction': self.direction,
            'direction_name': self.direction_name,
            'entry_price': self.entry_price,
            'quantity': self.quantity,
            'supplier': self.supplier,
            'settlement_price': self.settlement_price,
            'premium': self.premium,
            'physical_tons': self.physical_tons,
            'related_po': self.related_po,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'exit_price': self.exit_price,
            'exit_date': self.exit_date,
            'fee': self.fee,
            'profit_loss': self.profit_loss,
            'status': self.status,
            'status_name': self.status_name,
            'ma5': self.ma5,
            'ma10': self.ma10,
            'ma20': self.ma20,
            'rsi': self.rsi,
            'macd': self.macd,
            'entry_reason': self.entry_reason,
            'market_trend': self.market_trend,
            'trend_name': self.trend_name,
            'notes': self.notes,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
