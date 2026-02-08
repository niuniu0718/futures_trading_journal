"""
价格数据模型
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class SMMPrice:
    """SMM价格数据模型"""
    id: Optional[int] = None
    price_date: str = None
    highest_price: float = 0.0
    lowest_price: float = 0.0
    average_price: float = 0.0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        """初始化后处理"""
        if self.created_at is None:
            self.created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if self.updated_at is None:
            self.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'price_date': self.price_date,
            'highest_price': self.highest_price,
            'lowest_price': self.lowest_price,
            'average_price': self.average_price,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
