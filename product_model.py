"""
品种数据模型
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Product:
    """品种模型"""
    id: Optional[int] = None
    name: str = None  # 品种名称
    exchange: str = 'gfex'  # 默认交易所
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
