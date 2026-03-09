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
    purchase_quantity: Optional[float] = None  # 采购量（吨）
    purchase_price: Optional[float] = None  # 采购均价
    inventory_quantity: Optional[float] = None  # 库存数量（吨）- 已废弃，使用monthly_inventory
    inventory_cost: Optional[float] = None  # 库存成本 - 已废弃
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    # 非数据库字段 - 每月总库存（从monthly_inventory表获取）
    total_inventory: Optional[float] = None

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
            'purchase_quantity': self.purchase_quantity,
            'purchase_price': self.purchase_price,
            'inventory_quantity': self.inventory_quantity,
            'inventory_cost': self.inventory_cost,
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
            # 检查表是否存在
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='kpi_records'")
            table_exists = cursor.fetchone() is not None

            if not table_exists:
                # 创建新表
                conn.execute('''
                    CREATE TABLE kpi_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        month TEXT NOT NULL,
                        product_name TEXT NOT NULL,
                        purchase_quantity REAL,
                        purchase_price REAL,
                        inventory_quantity REAL,
                        inventory_cost REAL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        UNIQUE(month, product_name)
                    )
                ''')
            else:
                # 检查是否需要迁移
                cursor = conn.execute("PRAGMA table_info(kpi_records)")
                columns = [row['name'] for row in cursor.fetchall()]

                # 如果有旧字段但没有新字段，进行迁移
                if 'actual_quantity' in columns and 'purchase_quantity' not in columns:
                    # 备份数据
                    old_data = conn.execute('SELECT * FROM kpi_records').fetchall()

                    # 删除旧表
                    conn.execute('DROP TABLE kpi_records')

                    # 创建新表
                    conn.execute('''
                        CREATE TABLE kpi_records (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            month TEXT NOT NULL,
                            product_name TEXT NOT NULL,
                            purchase_quantity REAL,
                            purchase_price REAL,
                            inventory_quantity REAL,
                            inventory_cost REAL,
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL,
                            UNIQUE(month, product_name)
                        )
                    ''')

                    # 迁移数据（actual_quantity -> purchase_quantity, actual_avg_price -> purchase_price）
                    for row in old_data:
                        try:
                            conn.execute('''
                                INSERT INTO kpi_records
                                (month, product_name, purchase_quantity, purchase_price,
                                 created_at, updated_at)
                                VALUES (?, ?, ?, ?, ?, ?)
                            ''', (row['month'], row['product_name'],
                                  row.get('actual_quantity'), row.get('actual_avg_price'),
                                  row['created_at'], row['updated_at']))
                        except Exception:
                            pass  # 跳过重复键等错误

            conn.commit()

            # 创建每月库存表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS monthly_inventory (
                    month TEXT PRIMARY KEY,
                    inventory_quantity REAL,
                    updated_at TEXT NOT NULL
                )
            ''')
            conn.commit()

    def create_record(self, record):
        """创建新记录"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO kpi_records
                (month, product_name, purchase_quantity, purchase_price,
                 inventory_quantity, inventory_cost, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (record.month, record.product_name, record.purchase_quantity,
                  record.purchase_price, record.inventory_quantity, record.inventory_cost,
                  record.created_at, record.updated_at))
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
                    purchase_quantity=row['purchase_quantity'], purchase_price=row['purchase_price'],
                    inventory_quantity=row['inventory_quantity'], inventory_cost=row['inventory_cost'],
                    created_at=row['created_at'], updated_at=row['updated_at']
                )
            return None

    def get_record(self, month, product_name):
        """根据月份和品种获取记录"""
        with self.get_connection() as conn:
            row = conn.execute('SELECT * FROM kpi_records WHERE month = ? AND product_name = ?', (month, product_name)).fetchone()
            if row:
                return KPIRecord(
                    id=row['id'], month=row['month'], product_name=row['product_name'],
                    purchase_quantity=row['purchase_quantity'], purchase_price=row['purchase_price'],
                    inventory_quantity=row['inventory_quantity'], inventory_cost=row['inventory_cost'],
                    created_at=row['created_at'], updated_at=row['updated_at']
                )
            return None

    def get_all_records(self, product=None, year=None, order_by='month', order='ASC'):
        """获取所有记录"""
        with self.get_connection() as conn:
            query = 'SELECT * FROM kpi_records WHERE 1=1'
            params = []

            if product:
                query += ' AND product_name = ?'
                params.append(product)

            if year:
                query += ' AND month LIKE ?'
                params.append(f'{year}%')

            query += f' ORDER BY {order_by} {order}'
            rows = conn.execute(query, params).fetchall()

            records = []
            for row in rows:
                records.append(KPIRecord(
                    id=row['id'], month=row['month'], product_name=row['product_name'],
                    purchase_quantity=row['purchase_quantity'], purchase_price=row['purchase_price'],
                    inventory_quantity=row['inventory_quantity'], inventory_cost=row['inventory_cost'],
                    created_at=row['created_at'], updated_at=row['updated_at']
                ))
            return records

    def get_yearly_records(self, year):
        """获取指定年份的所有记录（1-12月 × 碳酸锂/氢氧化锂）"""
        products = ['碳酸锂', '氢氧化锂']
        records = []

        # 获取所有月度库存
        monthly_inventory = self.get_all_monthly_inventory(year)

        for month in range(1, 13):
            month_str = f"{year}-{month:02d}"
            month_inventory = monthly_inventory.get(month_str)

            for product in products:
                record = self.get_record(month_str, product)
                if not record:
                    # 创建空记录
                    record = KPIRecord(month=month_str, product_name=product)
                # 设置月度总库存（非数据库字段）
                record.total_inventory = month_inventory
                records.append(record)

        return records

    def update_field(self, record_id, field_name, value):
        """更新单个字段"""
        with self.get_connection() as conn:
            valid_fields = ['month', 'product_name', 'purchase_quantity', 'purchase_price',
                           'inventory_quantity', 'inventory_cost']
            if field_name not in valid_fields:
                raise ValueError(f"无效的字段名: {field_name}")

            updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn.execute(f'''
                UPDATE kpi_records
                SET {field_name} = ?, updated_at = ?
                WHERE id = ?
            ''', (value, updated_at, record_id))
            conn.commit()

            # 如果记录不存在，创建新记录
            if conn.total_changes == 0:
                return None

            return self.get_record_by_id(record_id)

    def update_or_create(self, month, product_name, **kwargs):
        """更新或创建记录"""
        record = self.get_record(month, product_name)

        if record:
            # 更新现有记录
            for key, value in kwargs.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            return self.update_record(record)
        else:
            # 创建新记录
            record = KPIRecord(month=month, product_name=product_name, **kwargs)
            return self.create_record(record)

    def update_record(self, record):
        """更新记录"""
        record.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with self.get_connection() as conn:
            conn.execute('''
                UPDATE kpi_records
                SET month=?, product_name=?, purchase_quantity=?, purchase_price=?,
                    inventory_quantity=?, inventory_cost=?, updated_at=?
                WHERE id=?
            ''', (record.month, record.product_name, record.purchase_quantity,
                  record.purchase_price, record.inventory_quantity, record.inventory_cost,
                  record.updated_at, record.id))
            conn.commit()
            return record

    def delete_record(self, record_id):
        """删除记录"""
        with self.get_connection() as conn:
            conn.execute('DELETE FROM kpi_records WHERE id = ?', (record_id,))
            conn.commit()

    # ==================== 每月库存管理 ====================

    def get_monthly_inventory(self, month):
        """获取指定月份的库存"""
        with self.get_connection() as conn:
            row = conn.execute('SELECT inventory_quantity FROM monthly_inventory WHERE month = ?', (month,)).fetchone()
            if row:
                return row['inventory_quantity']
            return None

    def set_monthly_inventory(self, month, quantity):
        """设置指定月份的库存"""
        with self.get_connection() as conn:
            updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn.execute('''
                INSERT INTO monthly_inventory (month, inventory_quantity, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(month) DO UPDATE SET
                    inventory_quantity = excluded.inventory_quantity,
                    updated_at = excluded.updated_at
            ''', (month, quantity, updated_at))
            conn.commit()

    def get_all_monthly_inventory(self, year):
        """获取指定年份的所有月度库存"""
        with self.get_connection() as conn:
            rows = conn.execute('SELECT month, inventory_quantity FROM monthly_inventory WHERE month LIKE ? ORDER BY month', (f'{year}%',)).fetchall()
            result = {}
            for row in rows:
                result[row['month']] = row['inventory_quantity']
            return result


# 创建全局实例
kpi_db = KPIDB()
