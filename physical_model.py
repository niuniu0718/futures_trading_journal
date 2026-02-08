"""
实物采购记录模型
"""
from datetime import datetime
from database import db


class PhysicalPurchase:
    """实物采购记录类"""

    def __init__(self, id=None, purchase_date=None, supplier=None, product_name=None,
                 quantity=None, unit_price=None, premium=None, total_amount=None,
                 po_number=None, delivery_date=None, status='pending', notes=None,
                 created_at=None, updated_at=None):
        self.id = id
        self.purchase_date = purchase_date  # 采购日期
        self.supplier = supplier  # 供应商
        self.product_name = product_name  # 品种名称
        self.quantity = quantity  # 数量（实物吨）
        self.unit_price = unit_price  # 单价
        self.premium = premium  # 贴水
        self.total_amount = total_amount  # 总金额
        self.po_number = po_number  # 采购订单号（PO号）
        self.delivery_date = delivery_date  # 交货日期
        self.status = status  # 状态: pending-未交货, completed-已交货
        self.notes = notes  # 备注
        self.created_at = created_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.updated_at = updated_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'purchase_date': self.purchase_date,
            'supplier': self.supplier,
            'product_name': self.product_name,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'premium': self.premium,
            'total_amount': self.total_amount,
            'po_number': self.po_number,
            'delivery_date': self.delivery_date,
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


class PhysicalPurchaseDB:
    """实物采购数据库管理类"""

    def __init__(self, db_path='data/trading_journal.db'):
        self.db_path = db_path
        self.init_table()

    def init_table(self):
        """初始化实物采购表和关联表"""
        with self.get_connection() as conn:
            # 检查并添加 premium 字段（如果不存在）
            conn.execute('''
                CREATE TABLE IF NOT EXISTS physical_purchases_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    purchase_date TEXT NOT NULL,
                    supplier TEXT,
                    product_name TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    unit_price REAL,
                    premium REAL DEFAULT 0,
                    total_amount REAL NOT NULL,
                    po_number TEXT,
                    delivery_date TEXT,
                    status TEXT DEFAULT 'pending',
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')

            # 采购-期货关联表（多对多）
            conn.execute('''
                CREATE TABLE IF NOT EXISTS purchase_trade_relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    purchase_id INTEGER NOT NULL,
                    trade_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (purchase_id) REFERENCES physical_purchases(id) ON DELETE CASCADE,
                    FOREIGN KEY (trade_id) REFERENCES trades(id) ON DELETE CASCADE,
                    UNIQUE(purchase_id, trade_id)
                )
            ''')

            # 检查是否需要迁移数据
            try:
                # 尝试查询 premium 字段
                conn.execute('SELECT premium FROM physical_purchases LIMIT 1')
            except Exception:
                # 字段不存在，需要迁移
                # 复制数据到新表
                conn.execute('''
                    INSERT INTO physical_purchases_new
                    (id, purchase_date, supplier, product_name, quantity, unit_price, total_amount,
                     po_number, delivery_date, status, notes, created_at, updated_at)
                    SELECT id, purchase_date, supplier, product_name, quantity, unit_price, total_amount,
                           po_number, delivery_date, status, notes, created_at, updated_at
                    FROM physical_purchases
                ''')

                # 删除旧表，重命名新表
                conn.execute('DROP TABLE physical_purchases')
                conn.execute('ALTER TABLE physical_purchases_new RENAME TO physical_purchases')

            conn.commit()

    def get_connection(self):
        """获取数据库连接"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def create_purchase(self, purchase, related_trade_ids=None):
        """创建新的实物采购记录"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO physical_purchases
                (purchase_date, supplier, product_name, quantity, unit_price, premium, total_amount,
                 po_number, delivery_date, status, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (purchase.purchase_date, purchase.supplier, purchase.product_name,
                  purchase.quantity, purchase.unit_price, purchase.premium, purchase.total_amount,
                  purchase.po_number, purchase.delivery_date,
                  purchase.status, purchase.notes, purchase.created_at, purchase.updated_at))
            conn.commit()
            purchase.id = cursor.lastrowid

            # 如果有关联的期货交易，创建关联关系
            if related_trade_ids:
                for trade_id in related_trade_ids:
                    if trade_id:  # 跳过空值
                        conn.execute('''
                            INSERT INTO purchase_trade_relations (purchase_id, trade_id, created_at)
                            VALUES (?, ?, ?)
                        ''', (purchase.id, trade_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                conn.commit()

            return purchase

    def add_trade_relation(self, purchase_id, trade_id):
        """添加采购-期货关联"""
        with self.get_connection() as conn:
            try:
                conn.execute('''
                    INSERT INTO purchase_trade_relations (purchase_id, trade_id, created_at)
                    VALUES (?, ?, ?)
                ''', (purchase_id, trade_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                conn.commit()
                return True
            except Exception:
                return False  # 关联已存在或其他错误

    def remove_trade_relation(self, purchase_id, trade_id):
        """删除采购-期货关联"""
        with self.get_connection() as conn:
            conn.execute('''
                DELETE FROM purchase_trade_relations WHERE purchase_id = ? AND trade_id = ?
            ''', (purchase_id, trade_id))
            conn.commit()

    def get_purchase_by_id(self, purchase_id):
        """根据ID获取实物采购记录"""
        with self.get_connection() as conn:
            row = conn.execute('SELECT * FROM physical_purchases WHERE id = ?', (purchase_id,)).fetchone()
            if row:
                return PhysicalPurchase(
                    id=row['id'],
                    purchase_date=row['purchase_date'],
                    supplier=row['supplier'],
                    product_name=row['product_name'],
                    quantity=row['quantity'],
                    unit_price=row['unit_price'],
                    premium=row['premium'],
                    total_amount=row['total_amount'],
                    po_number=row['po_number'],
                    delivery_date=row['delivery_date'],
                    status=row['status'],
                    notes=row['notes'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
            return None

    def get_related_trades(self, purchase_id):
        """获取采购记录关联的所有期货交易"""
        with self.get_connection() as conn:
            rows = conn.execute('''
                SELECT t.* FROM trades t
                INNER JOIN purchase_trade_relations ptr ON t.id = ptr.trade_id
                WHERE ptr.purchase_id = ?
                ORDER BY t.trade_date DESC
            ''', (purchase_id,)).fetchall()

            from models import Trade
            trades = []
            for row in rows:
                trades.append(Trade(
                    id=row['id'],
                    trade_date=row['trade_date'],
                    exchange=row['exchange'],
                    product_name=row['product_name'],
                    contract=row['contract'],
                    direction=row['direction'],
                    entry_price=row['entry_price'],
                    quantity=row['quantity'],
                    supplier=row['supplier'],
                    settlement_price=row['settlement_price'],
                    premium=row['premium'],
                    physical_tons=row['physical_tons'],
                    related_po=row['related_po'],
                    stop_loss=row['stop_loss'],
                    take_profit=row['take_profit'],
                    exit_price=row['exit_price'],
                    exit_date=row['exit_date'],
                    fee=row['fee'],
                    profit_loss=row['profit_loss'],
                    status=row['status'],
                    ma5=row['ma5'],
                    ma10=row['ma10'],
                    ma20=row['ma20'],
                    rsi=row['rsi'],
                    macd=row['macd'],
                    entry_reason=row['entry_reason'],
                    market_trend=row['market_trend'],
                    notes=row['notes'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                ))
            return trades

    def get_related_purchases(self, trade_id):
        """获取期货交易关联的所有采购记录"""
        with self.get_connection() as conn:
            rows = conn.execute('''
                SELECT pp.* FROM physical_purchases pp
                INNER JOIN purchase_trade_relations ptr ON pp.id = ptr.purchase_id
                WHERE ptr.trade_id = ?
                ORDER BY pp.purchase_date DESC
            ''', (trade_id,)).fetchall()

            purchases = []
            for row in rows:
                purchases.append(PhysicalPurchase(
                    id=row['id'],
                    purchase_date=row['purchase_date'],
                    supplier=row['supplier'],
                    product_name=row['product_name'],
                    quantity=row['quantity'],
                    unit_price=row['unit_price'],
                    premium=row['premium'],
                    total_amount=row['total_amount'],
                    po_number=row['po_number'],
                    delivery_date=row['delivery_date'],
                    status=row['status'],
                    notes=row['notes'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                ))
            return purchases

    def get_all_purchases(self, status=None, supplier=None, product=None, order_by='purchase_date', order='DESC'):
        """获取所有实物采购记录"""
        with self.get_connection() as conn:
            query = 'SELECT * FROM physical_purchases WHERE 1=1'
            params = []

            if status:
                query += ' AND status = ?'
                params.append(status)

            if supplier:
                query += ' AND supplier = ?'
                params.append(supplier)

            if product:
                query += ' AND product_name = ?'
                params.append(product)

            query += f' ORDER BY {order_by} {order}'

            rows = conn.execute(query, params).fetchall()
            purchases = []
            for row in rows:
                purchases.append(PhysicalPurchase(
                    id=row['id'],
                    purchase_date=row['purchase_date'],
                    supplier=row['supplier'],
                    product_name=row['product_name'],
                    quantity=row['quantity'],
                    unit_price=row['unit_price'],
                    premium=row['premium'],
                    total_amount=row['total_amount'],
                    po_number=row['po_number'],
                    delivery_date=row['delivery_date'],
                    status=row['status'],
                    notes=row['notes'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                ))
            return purchases

    def update_purchase(self, purchase, related_trade_ids=None):
        """更新实物采购记录"""
        purchase.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with self.get_connection() as conn:
            conn.execute('''
                UPDATE physical_purchases
                SET purchase_date=?, supplier=?, product_name=?, quantity=?, unit_price=?,
                    premium=?, total_amount=?, po_number=?, delivery_date=?,
                    status=?, notes=?, updated_at=?
                WHERE id=?
            ''', (purchase.purchase_date, purchase.supplier, purchase.product_name,
                  purchase.quantity, purchase.unit_price, purchase.premium, purchase.total_amount,
                  purchase.po_number, purchase.delivery_date,
                  purchase.status, purchase.notes, purchase.updated_at, purchase.id))
            conn.commit()

            # 更新关联的期货交易
            # 先删除旧的关联
            conn.execute('DELETE FROM purchase_trade_relations WHERE purchase_id = ?', (purchase.id,))

            # 添加新的关联
            if related_trade_ids:
                for trade_id in related_trade_ids:
                    if trade_id:  # 跳过空值
                        conn.execute('''
                            INSERT INTO purchase_trade_relations (purchase_id, trade_id, created_at)
                            VALUES (?, ?, ?)
                        ''', (purchase.id, trade_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                conn.commit()

            return purchase

    def delete_purchase(self, purchase_id):
        """删除实物采购记录"""
        with self.get_connection() as conn:
            conn.execute('DELETE FROM physical_purchases WHERE id = ?', (purchase_id,))
            conn.commit()

    def get_distinct_suppliers(self):
        """获取所有供应商列表"""
        with self.get_connection() as conn:
            rows = conn.execute('SELECT DISTINCT supplier FROM physical_purchases WHERE supplier IS NOT NULL ORDER BY supplier').fetchall()
            return [row['supplier'] for row in rows]

    def get_distinct_products(self):
        """获取所有品种列表"""
        with self.get_connection() as conn:
            rows = conn.execute('SELECT DISTINCT product_name FROM physical_purchases ORDER BY product_name').fetchall()
            return [row['product_name'] for row in rows]


# 创建全局实例
physical_db = PhysicalPurchaseDB()
