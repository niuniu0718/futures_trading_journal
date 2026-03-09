"""
KPI追踪模型 - Actual + Forecast
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class KPIRecord:
    """KPI记录数据模型"""
    id: Optional[int] = None
    month: str = None  # 月份 YYYY-MM
    product_name: str = None  # 品种：碳酸锂/氢氧化锂
    actual_quantity: Optional[float] = None  # 实际采购量（吨）
    actual_avg_price: Optional[float] = None  # 实际均价
    forecast_quantity: Optional[float] = None  # 预测采购量（吨）
    forecast_avg_price: Optional[float] = None  # 预测均价
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
            'month': self.month,
            'product_name': self.product_name,
            'actual_quantity': self.actual_quantity,
            'actual_avg_price': self.actual_avg_price,
            'forecast_quantity': self.forecast_quantity,
            'forecast_avg_price': self.forecast_avg_price,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


class KPIDB:
    """KPI数据库管理类"""

    def __init__(self, db_path='data/trading_journal.db'):
        self.db_path = db_path
        self.init_table()

    def get_connection(self):
        """获取数据库连接"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_table(self):
        """初始化KPI表"""
        with self.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS kpi_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    month TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    actual_quantity REAL,
                    actual_avg_price REAL,
                    forecast_quantity REAL,
                    forecast_avg_price REAL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(month, product_name)
                )
            ''')
            conn.commit()

    def create_record(self, record):
        """创建新记录"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO kpi_records
                (month, product_name, actual_quantity, actual_avg_price,
                 forecast_quantity, forecast_avg_price, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (record.month, record.product_name, record.actual_quantity,
                  record.actual_avg_price, record.forecast_quantity,
                  record.forecast_avg_price, record.created_at, record.updated_at))
            conn.commit()
            record.id = cursor.lastrowid
            return record

    def get_record_by_id(self, record_id):
        """根据ID获取记录"""
        with self.get_connection() as conn:
            row = conn.execute('SELECT * FROM kpi_records WHERE id = ?', (record_id,)).fetchone()
            if row:
                return KPIRecord(
                    id=row['id'], month=row['month'], product_name=row['product_name'],
                    actual_quantity=row['actual_quantity'], actual_avg_price=row['actual_avg_price'],
                    forecast_quantity=row['forecast_quantity'], forecast_avg_price=row['forecast_avg_price'],
                    created_at=row['created_at'], updated_at=row['updated_at']
                )
            return None

    def get_all_records(self, product=None, order_by='month', order='DESC'):
        """获取所有记录"""
        with self.get_connection() as conn:
            query = 'SELECT * FROM kpi_records WHERE 1=1'
            params = []

            if product:
                query += ' AND product_name = ?'
                params.append(product)

            query += f' ORDER BY {order_by} {order}'
            rows = conn.execute(query, params).fetchall()

            records = []
            for row in rows:
                records.append(KPIRecord(
                    id=row['id'], month=row['month'], product_name=row['product_name'],
                    actual_quantity=row['actual_quantity'], actual_avg_price=row['actual_avg_price'],
                    forecast_quantity=row['forecast_quantity'], forecast_avg_price=row['forecast_avg_price'],
                    created_at=row['created_at'], updated_at=row['updated_at']
                ))
            return records

    def update_record(self, record):
        """更新记录"""
        record.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with self.get_connection() as conn:
            conn.execute('''
                UPDATE kpi_records
                SET month=?, product_name=?, actual_quantity=?, actual_avg_price=?,
                    forecast_quantity=?, forecast_avg_price=?, updated_at=?
                WHERE id=?
            ''', (record.month, record.product_name, record.actual_quantity,
                  record.actual_avg_price, record.forecast_quantity,
                  record.forecast_avg_price, record.updated_at, record.id))
            conn.commit()
            return record

    def delete_record(self, record_id):
        """删除记录"""
        with self.get_connection() as conn:
            conn.execute('DELETE FROM kpi_records WHERE id = ?', (record_id,))
            conn.commit()

    def get_monthly_stats(self, month=None):
        """获取月度统计数据"""
        with self.get_connection() as conn:
            if month:
                query = '''
                    SELECT product_name,
                           SUM(actual_quantity) as total_actual_qty,
                           AVG(actual_avg_price) as avg_actual_price,
                           SUM(forecast_quantity) as total_forecast_qty,
                           AVG(forecast_avg_price) as avg_forecast_price
                    FROM kpi_records
                    WHERE month = ? AND actual_quantity IS NOT NULL
                    GROUP BY product_name
                '''
                rows = conn.execute(query, (month,)).fetchall()
            else:
                # 获取最新月份的统计
                query = '''
                    SELECT product_name,
                           SUM(actual_quantity) as total_actual_qty,
                           AVG(actual_avg_price) as avg_actual_price,
                           SUM(forecast_quantity) as total_forecast_qty,
                           AVG(forecast_avg_price) as avg_forecast_price
                    FROM kpi_records
                    WHERE month = (SELECT MAX(month) FROM kpi_records) AND actual_quantity IS NOT NULL
                    GROUP BY product_name
                '''
                rows = conn.execute(query).fetchall()

            stats = {}
            for row in rows:
                stats[row['product_name']] = {
                    'total_actual_qty': row['total_actual_qty'] or 0,
                    'avg_actual_price': row['avg_actual_price'] or 0,
                    'total_forecast_qty': row['total_forecast_qty'] or 0,
                    'avg_forecast_price': row['avg_forecast_price'] or 0
                }
            return stats


# 创建全局实例
kpi_db = KPIDB()
