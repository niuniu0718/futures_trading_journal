"""
账务管理模块
用于核销有供应商和结算价的交易订单
"""
import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Any
from loguru import logger
from config import DATABASE_PATH
from database import DatabaseManager


class BillingRecord:
    """账务核销记录"""

    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.trade_id = kwargs.get('trade_id')
        self.billing_month = kwargs.get('billing_month')  # 核销月份
        self.base_month = kwargs.get('base_month')  # Base月份（格式: 2024-01）
        self.base_price = kwargs.get('base_price')  # Base价格（历史保存的SMM均价）
        self.current_smm_price = kwargs.get('current_smm_price')  # 当前SMM均价（动态获取）
        self.settlement_price = kwargs.get('settlement_price')  # 结算价
        self.quantity = kwargs.get('quantity')  # 数量
        self.physical_tons = kwargs.get('physical_tons')  # 实物吨
        self.settlement_amount = kwargs.get('settlement_amount')  # 结算金额
        self.discount = kwargs.get('discount')  # 折扣（相对于SMM的折扣%）
        self.related_po = kwargs.get('related_po')  # 关联PO
        self.notes = kwargs.get('notes')
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')

        # 关联的交易信息
        self.trade_date = kwargs.get('trade_date')
        self.supplier = kwargs.get('supplier')
        self.product_name = kwargs.get('product_name')
        self.contract = kwargs.get('contract')

    @property
    def display_price(self):
        """显示价格（优先使用当前SMM价格，如果没有则使用保存的价格）"""
        return self.current_smm_price if self.current_smm_price is not None else self.base_price

    @property
    def current_discount(self):
        """基于当前SMM价格计算折扣"""
        if self.display_price and self.display_price > 0:
            return ((self.display_price - self.settlement_price) / self.display_price) * 100
        return 0

    @property
    def billing_month_display(self):
        """格式化显示核销月份"""
        if self.billing_month and '-' in str(self.billing_month):
            year, month = self.billing_month.split('-')
            return f"{year}年{int(month)}月"
        return self.billing_month or ""

    @property
    def base_month_display(self):
        """格式化显示Base月份"""
        if self.base_month and '-' in str(self.base_month):
            year, month = self.base_month.split('-')
            return f"{year}年{int(month)}月"
        return self.base_month or ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'trade_id': self.trade_id,
            'billing_month': self.billing_month,
            'billing_month_display': self.billing_month_display,
            'base_month': self.base_month,
            'base_month_display': self.base_month_display,
            'base_price': self.base_price,
            'current_smm_price': self.current_smm_price,
            'display_price': self.display_price,
            'settlement_price': self.settlement_price,
            'quantity': self.quantity,
            'physical_tons': self.physical_tons,
            'settlement_amount': self.settlement_amount,
            'discount': self.discount,
            'current_discount': self.current_discount,
            'related_po': self.related_po,
            'notes': self.notes,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'trade_date': self.trade_date,
            'supplier': self.supplier,
            'product_name': self.product_name,
            'contract': self.contract
        }


class BillingDatabase:
    """账务数据库管理类"""

    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self.init_database()

    @staticmethod
    def get_connection():
        """获取数据库连接"""
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        """初始化账务表"""
        conn = self.get_connection()
        try:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS billing_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id INTEGER NOT NULL,
                    billing_month TEXT NOT NULL,
                    base_month TEXT NOT NULL,
                    base_price REAL NOT NULL,
                    settlement_price REAL NOT NULL,
                    quantity REAL NOT NULL,
                    physical_tons REAL NOT NULL,
                    settlement_amount REAL NOT NULL,
                    discount REAL NOT NULL,
                    notes TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY (trade_id) REFERENCES trades(id) ON DELETE CASCADE,
                    UNIQUE(trade_id)
                )
            ''')
            conn.commit()
            logger.info("账务数据库初始化完成")
        finally:
            conn.close()

    def get_available_trades(self) -> List[Dict[str, Any]]:
        """获取可用于核销的交易记录（有供应商和结算价）"""
        conn = self.get_connection()
        try:
            # 获取有供应商和结算价，且未被核销的交易
            cursor = conn.execute('''
                SELECT t.id, t.trade_date, t.supplier, t.product_name, t.contract,
                       t.settlement_price, t.quantity, t.physical_tons, t.related_po
                FROM trades t
                WHERE t.supplier IS NOT NULL AND t.supplier != ''
                  AND t.settlement_price IS NOT NULL
                  AND t.id NOT IN (SELECT trade_id FROM billing_records)
                ORDER BY t.trade_date DESC
            ''')

            trades = []
            for row in cursor.fetchall():
                trades.append({
                    'id': row['id'],
                    'trade_date': row['trade_date'],
                    'supplier': row['supplier'],
                    'product_name': row['product_name'],
                    'contract': row['contract'],
                    'settlement_price': row['settlement_price'],
                    'quantity': row['quantity'],
                    'physical_tons': row['physical_tons'] or round(row['quantity'] * 1.13),
                    'related_po': row['related_po']
                })

            return trades
        finally:
            conn.close()

    def create_billing(self, trade_id: int, billing_month: str, base_month: str,
                      base_price: float, related_po: str = None, notes: str = None) -> int:
        """创建核销记录"""
        conn = self.get_connection()
        try:
            # 获取交易信息
            cursor = conn.execute('''
                SELECT settlement_price, quantity, physical_tons
                FROM trades
                WHERE id = ?
            ''', (trade_id,))

            row = cursor.fetchone()
            if not row:
                raise ValueError(f"交易记录 {trade_id} 不存在")

            settlement_price = row['settlement_price']
            quantity = row['quantity']
            physical_tons = row['physical_tons'] or round(quantity * 1.13)

            # 计算结算金额和折扣
            settlement_amount = settlement_price * quantity
            discount = ((base_price - settlement_price) / base_price) * 100 if base_price else 0

            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            cursor = conn.execute('''
                INSERT INTO billing_records (
                    trade_id, billing_month, base_month, base_price,
                    settlement_price, quantity, physical_tons,
                    settlement_amount, discount, related_po, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (trade_id, billing_month, base_month, base_price,
                   settlement_price, quantity, physical_tons,
                   settlement_amount, discount, related_po, notes, now, now))

            # 如果有关联PO，同步更新到交易记录
            if related_po:
                conn.execute('''
                    UPDATE trades SET related_po = ?, updated_at = ?
                    WHERE id = ?
                ''', (related_po, now, trade_id))
                logger.info(f"同步关联PO到交易记录: trade_id={trade_id}, related_po={related_po}")

            conn.commit()
            logger.info(f"创建核销记录: trade_id={trade_id}, base_month={base_month}, related_po={related_po}")
            return cursor.lastrowid
        finally:
            conn.close()

    def get_all_billings(self, month_filter: str = None, supplier_filter: str = None) -> List[BillingRecord]:
        """获取所有核销记录"""
        conn = self.get_connection()
        try:
            query = '''
                SELECT br.*, t.trade_date, t.supplier, t.product_name, t.contract
                FROM billing_records br
                JOIN trades t ON br.trade_id = t.id
                WHERE 1=1
            '''
            params = []

            if month_filter:
                query += ' AND br.base_month = ?'
                params.append(month_filter)

            if supplier_filter:
                query += ' AND t.supplier = ?'
                params.append(supplier_filter)

            query += ' ORDER BY br.billing_month DESC'

            cursor = conn.execute(query, params)
            records = []

            # 初始化数据库连接用于获取SMM价格
            smm_db = DatabaseManager()

            for row in cursor.fetchall():
                # 获取当前SMM价格
                current_smm_price = None
                base_month = row['base_month']
                if base_month and '-' in str(base_month):
                    try:
                        year, month = base_month.split('-')
                        smm_prices = smm_db.get_smm_prices_by_month(int(year), int(month))
                        if smm_prices:
                            current_smm_price = sum(p.average_price for p in smm_prices) / len(smm_prices)
                    except Exception as e:
                        logger.warning(f"获取SMM价格失败: base_month={base_month}, error={e}")

                record = BillingRecord(
                    id=row['id'],
                    trade_id=row['trade_id'],
                    billing_month=row['billing_month'],
                    base_month=row['base_month'],
                    base_price=row['base_price'],
                    current_smm_price=current_smm_price,
                    settlement_price=row['settlement_price'],
                    quantity=row['quantity'],
                    physical_tons=row['physical_tons'],
                    settlement_amount=row['settlement_amount'],
                    discount=row['discount'],
                    related_po=row['related_po'],
                    notes=row['notes'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    trade_date=row['trade_date'],
                    supplier=row['supplier'],
                    product_name=row['product_name'],
                    contract=row['contract']
                )
                records.append(record)

            return records
        finally:
            conn.close()

    def get_billing_by_id(self, billing_id: int) -> Optional[BillingRecord]:
        """获取单条核销记录"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                SELECT br.*, t.trade_date, t.supplier, t.product_name, t.contract
                FROM billing_records br
                JOIN trades t ON br.trade_id = t.id
                WHERE br.id = ?
            ''', (billing_id,))

            row = cursor.fetchone()
            if not row:
                return None

            return BillingRecord(
                id=row['id'],
                trade_id=row['trade_id'],
                billing_month=row['billing_month'],
                base_month=row['base_month'],
                base_price=row['base_price'],
                settlement_price=row['settlement_price'],
                quantity=row['quantity'],
                physical_tons=row['physical_tons'],
                settlement_amount=row['settlement_amount'],
                discount=row['discount'],
                related_po=row['related_po'],
                notes=row['notes'],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                trade_date=row['trade_date'],
                supplier=row['supplier'],
                product_name=row['product_name'],
                contract=row['contract']
            )
        finally:
            conn.close()

    def update_billing(self, billing_id: int, billing_month: str = None,
                      base_month: str = None, base_price: float = None,
                      related_po: str = None, notes: str = None) -> bool:
        """更新核销记录"""
        conn = self.get_connection()
        try:
            record = self.get_billing_by_id(billing_id)
            if not record:
                return False

            # 如果更新了base_month或base_price，需要重新计算折扣
            if base_month or base_price:
                if base_month:
                    record.base_month = base_month
                if base_price:
                    record.base_price = base_price

                record.discount = ((record.base_price - record.settlement_price) / record.base_price) * 100 if record.base_price else 0

            if billing_month:
                record.billing_month = billing_month
            if related_po is not None:
                record.related_po = related_po
            if notes is not None:
                record.notes = notes

            record.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            conn.execute('''
                UPDATE billing_records SET
                    billing_month = ?,
                    base_month = ?,
                    base_price = ?,
                    discount = ?,
                    related_po = ?,
                    notes = ?,
                    updated_at = ?
                WHERE id = ?
            ''', (record.billing_month, record.base_month, record.base_price,
                   record.discount, record.related_po, record.notes, record.updated_at, billing_id))

            # 如果更新了关联PO，同步更新到交易记录
            if related_po is not None:
                conn.execute('''
                    UPDATE trades SET related_po = ?, updated_at = ?
                    WHERE id = ?
                ''', (related_po, record.updated_at, record.trade_id))
                logger.info(f"同步关联PO到交易记录: trade_id={record.trade_id}, related_po={related_po}")

            conn.commit()
            logger.info(f"更新核销记录: id={billing_id}")
            return True
        finally:
            conn.close()

    def delete_billing(self, billing_id: int) -> bool:
        """删除核销记录"""
        conn = self.get_connection()
        try:
            conn.execute('DELETE FROM billing_records WHERE id = ?', (billing_id,))
            conn.commit()
            logger.info(f"删除核销记录: id={billing_id}")
            return True
        finally:
            conn.close()

    def get_billing_summary(self, month_filter: str = None,
                          supplier_filter: str = None) -> Dict[str, Any]:
        """获取核销汇总统计（使用当前SMM价格计算折扣）"""
        conn = self.get_connection()
        try:
            query = '''
                SELECT
                    COUNT(*) as count,
                    SUM(br.quantity) as total_quantity,
                    SUM(br.physical_tons) as total_physical_tons,
                    SUM(br.settlement_amount) as total_settlement_amount,
                    AVG(br.settlement_price) as avg_settlement_price,
                    AVG(br.base_price) as avg_base_price
                FROM billing_records br
                JOIN trades t ON br.trade_id = t.id
                WHERE 1=1
            '''
            params = []

            if month_filter:
                query += ' AND br.base_month = ?'
                params.append(month_filter)

            if supplier_filter:
                query += ' AND t.supplier = ?'
                params.append(supplier_filter)

            cursor = conn.execute(query, params)
            row = cursor.fetchone()

            # 获取所有核销记录以动态计算折扣
            billings = self.get_all_billings(
                month_filter=month_filter,
                supplier_filter=supplier_filter
            )

            # 基于当前SMM价格计算平均折扣
            current_discounts = []
            current_base_prices = []
            for billing in billings:
                if billing.display_price and billing.display_price > 0:
                    current_discounts.append(billing.current_discount)
                    current_base_prices.append(billing.display_price)

            avg_discount = sum(current_discounts) / len(current_discounts) if current_discounts else 0
            avg_base_price = sum(current_base_prices) / len(current_base_prices) if current_base_prices else 0

            return {
                'count': row['count'] or 0,
                'total_quantity': row['total_quantity'] or 0,
                'total_physical_tons': row['total_physical_tons'] or 0,
                'total_settlement_amount': row['total_settlement_amount'] or 0,
                'avg_settlement_price': row['avg_settlement_price'] or 0,
                'avg_base_price': avg_base_price,
                'avg_discount': avg_discount
            }
        finally:
            conn.close()

    def get_distinct_suppliers(self) -> List[str]:
        """获取所有供应商列表"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                SELECT DISTINCT supplier
                FROM billing_records br
                JOIN trades t ON br.trade_id = t.id
                WHERE supplier IS NOT NULL AND supplier != ''
                ORDER BY supplier
            ''')
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_distinct_base_months(self) -> List[str]:
        """获取所有base月份列表"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                SELECT DISTINCT base_month
                FROM billing_records
                ORDER BY base_month DESC
            ''')
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()


# 创建全局账务数据库实例
billing_db = BillingDatabase()
