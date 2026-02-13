"""
数据库管理模块
"""
import sqlite3
from contextlib import contextmanager
from typing import List, Optional, Dict, Any
from loguru import logger
from config import DATABASE_PATH
from models import Trade
from smm_model import SMMPrice
from futures_model import FuturesPrice
from product_model import Product
from migrations import migration_manager


class DatabaseManager:
    """数据库管理类"""

    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._run_migrations()  # 先执行迁移
        self.init_database()  # 再初始化数据库

    def _run_migrations(self):
        """执行数据库迁移"""
        if migration_manager.migrate():
            logger.info("数据库迁移检查完成")
        else:
            logger.warning("数据库迁移失败，可能存在数据问题")

    @contextmanager
    def get_connection(self):
        """获取数据库连接上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            conn.close()

    def init_database(self):
        """初始化数据库表"""
        with self.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_date TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    contract TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    quantity REAL NOT NULL,
                    supplier TEXT,
                    settlement_price REAL,
                    premium REAL,
                    physical_tons REAL,
                    related_po TEXT,
                    stop_loss REAL,
                    take_profit REAL,
                    exit_price REAL,
                    exit_date TEXT,
                    fee REAL DEFAULT 0,
                    profit_loss REAL DEFAULT 0,
                    status TEXT NOT NULL,
                    ma5 REAL,
                    ma10 REAL,
                    ma20 REAL,
                    rsi REAL,
                    macd REAL,
                    entry_reason TEXT,
                    market_trend TEXT,
                    notes TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')

            # 创建SMM价格表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS smm_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    price_date TEXT NOT NULL UNIQUE,
                    highest_price REAL NOT NULL,
                    lowest_price REAL NOT NULL,
                    average_price REAL NOT NULL,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')

            # 创建期货价格表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS futures_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    price_date TEXT NOT NULL UNIQUE,
                    highest_price REAL NOT NULL,
                    lowest_price REAL NOT NULL,
                    average_price REAL NOT NULL,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')

            # 创建品种表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    exchange TEXT NOT NULL DEFAULT 'gfex',
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')

            # 插入默认品种数据
            cursor = conn.execute('SELECT COUNT(*) FROM products')
            if cursor.fetchone()[0] == 0:
                default_products = [
                    ('工碳', 'gfex'),
                    ('电碳', 'gfex'),
                ]
                for name, exchange in default_products:
                    conn.execute('INSERT INTO products (name, exchange, created_at, updated_at) VALUES (?, ?, datetime("now"), datetime("now"))', (name, exchange))
                logger.info("插入默认品种数据")

            logger.info("数据库初始化完成")

    def create_trade(self, trade: Trade) -> int:
        """创建交易记录"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO trades (
                    trade_date, exchange, product_name, contract, direction,
                    entry_price, quantity, stop_loss, take_profit, exit_price,
                    exit_date, fee, profit_loss, status, ma5, ma10, ma20,
                    rsi, macd, entry_reason, market_trend, notes,
                    created_at, updated_at, supplier, settlement_price, premium,
                    physical_tons, related_po
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade.trade_date, trade.exchange, trade.product_name, trade.contract,
                trade.direction, trade.entry_price, trade.quantity, trade.stop_loss,
                trade.take_profit, trade.exit_price, trade.exit_date, trade.fee,
                trade.profit_loss, trade.status, trade.ma5, trade.ma10, trade.ma20,
                trade.rsi, trade.macd, trade.entry_reason, trade.market_trend,
                trade.notes, trade.created_at, trade.updated_at, trade.supplier,
                trade.settlement_price, trade.premium, trade.physical_tons, trade.related_po
            ))
            return cursor.lastrowid

    def get_trade(self, trade_id: int) -> Optional[Trade]:
        """获取单条交易记录"""
        with self.get_connection() as conn:
            row = conn.execute('SELECT * FROM trades WHERE id = ?', (trade_id,)).fetchone()
            if row:
                return self._row_to_trade(row)
            return None

    def get_all_trades(self, status: Optional[str] = None, product: Optional[str] = None,
                       order_by: str = 'trade_date', order: str = 'DESC') -> List[Trade]:
        """获取所有交易记录"""
        query = 'SELECT * FROM trades WHERE 1=1'
        params = []

        if status:
            query += ' AND status = ?'
            params.append(status)

        if product:
            query += ' AND product_name = ?'
            params.append(product)

        query += f' ORDER BY {order_by} {order}'

        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_trade(row) for row in rows]

    def update_trade(self, trade: Trade) -> bool:
        """更新交易记录"""
        with self.get_connection() as conn:
            conn.execute('''
                UPDATE trades SET
                    trade_date = ?, exchange = ?, product_name = ?, contract = ?,
                    direction = ?, entry_price = ?, quantity = ?, supplier = ?,
                    settlement_price = ?, premium = ?, physical_tons = ?,
                    related_po = ?, stop_loss = ?, take_profit = ?, exit_price = ?,
                    exit_date = ?, fee = ?, profit_loss = ?, status = ?,
                    ma5 = ?, ma10 = ?, ma20 = ?, rsi = ?, macd = ?,
                    entry_reason = ?, market_trend = ?, notes = ?, updated_at = ?
                WHERE id = ?
            ''', (
                trade.trade_date, trade.exchange, trade.product_name, trade.contract,
                trade.direction, trade.entry_price, trade.quantity, trade.supplier,
                trade.settlement_price, trade.premium, trade.physical_tons, trade.related_po,
                trade.stop_loss, trade.take_profit, trade.exit_price, trade.exit_date,
                trade.fee, trade.profit_loss, trade.status, trade.ma5, trade.ma10,
                trade.ma20, trade.rsi, trade.macd, trade.entry_reason,
                trade.market_trend, trade.notes, trade.updated_at, trade.id
            ))
            return conn.total_changes > 0

    def delete_trade(self, trade_id: int) -> bool:
        """删除交易记录"""
        with self.get_connection() as conn:
            conn.execute('DELETE FROM trades WHERE id = ?', (trade_id,))
            return conn.total_changes > 0

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计数据"""
        with self.get_connection() as conn:
            # 总交易数
            total_trades = conn.execute('SELECT COUNT(*) FROM trades').fetchone()[0]

            # 已平仓交易数
            closed_trades = conn.execute(
                'SELECT COUNT(*) FROM trades WHERE status = "closed"'
            ).fetchone()[0]

            # 盈利交易数
            profitable_trades = conn.execute(
                'SELECT COUNT(*) FROM trades WHERE status = "closed" AND profit_loss > 0'
            ).fetchone()[0]

            # 总盈亏
            total_profit_loss = conn.execute(
                'SELECT COALESCE(SUM(profit_loss), 0) FROM trades WHERE status = "closed"'
            ).fetchone()[0]

            # 最大盈利
            max_profit = conn.execute(
                'SELECT COALESCE(MAX(profit_loss), 0) FROM trades WHERE status = "closed"'
            ).fetchone()[0]

            # 最大亏损
            max_loss = conn.execute(
                'SELECT COALESCE(MIN(profit_loss), 0) FROM trades WHERE status = "closed"'
            ).fetchone()[0]

            # 按品种统计
            product_stats = conn.execute('''
                SELECT
                    product_name,
                    COUNT(*) as count,
                    SUM(CASE WHEN status = "closed" THEN profit_loss ELSE 0 END) as total_pl
                FROM trades
                GROUP BY product_name
                ORDER BY total_pl DESC
            ''').fetchall()

            # 胜率
            win_rate = (profitable_trades / closed_trades * 100) if closed_trades > 0 else 0

            # 平均盈亏
            avg_profit_loss = conn.execute(
                'SELECT COALESCE(AVG(profit_loss), 0) FROM trades WHERE status = "closed"'
            ).fetchone()[0]

            return {
                'total_trades': total_trades,
                'open_trades': total_trades - closed_trades,
                'closed_trades': closed_trades,
                'profitable_trades': profitable_trades,
                'losing_trades': closed_trades - profitable_trades,
                'total_profit_loss': total_profit_loss,
                'max_profit': max_profit,
                'max_loss': max_loss,
                'win_rate': win_rate,
                'avg_profit_loss': avg_profit_loss,
                'product_stats': [dict(row) for row in product_stats]
            }

    def get_weighted_average_prices(self) -> Dict[str, float]:
        """获取加权平均价格"""
        with self.get_connection() as conn:
            # 计算加权平均开仓价
            result = conn.execute('''
                SELECT
                    SUM(entry_price * quantity) / SUM(quantity) as avg_entry_price,
                    SUM(CASE WHEN settlement_price IS NOT NULL THEN settlement_price * quantity ELSE 0 END) /
                        SUM(CASE WHEN settlement_price IS NOT NULL THEN quantity ELSE 0 END) as avg_settlement_price
                FROM trades
            ''').fetchone()

            return {
                'avg_entry_price': result[0] if result and result[0] else 0.0,
                'avg_settlement_price': result[1] if result and result[1] else 0.0
            }

    def get_distinct_values(self, field: str) -> List[str]:
        """获取字段的不重复值列表"""
        with self.get_connection() as conn:
            rows = conn.execute(f'SELECT DISTINCT {field} FROM trades ORDER BY {field}').fetchall()
            return [row[0] for row in rows if row[0]]

    # ==================== SMM价格管理 ====================

    def create_smm_price(self, smm_price: SMMPrice) -> int:
        """创建SMM价格记录"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO smm_prices (
                    price_date, highest_price, lowest_price, average_price,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                smm_price.price_date, smm_price.highest_price,
                smm_price.lowest_price, smm_price.average_price,
                smm_price.created_at, smm_price.updated_at
            ))
            return cursor.lastrowid

    def get_smm_price(self, price_id: int) -> Optional[SMMPrice]:
        """获取单条SMM价格记录"""
        with self.get_connection() as conn:
            row = conn.execute('SELECT * FROM smm_prices WHERE id = ?', (price_id,)).fetchone()
            if row:
                return self._row_to_smm_price(row)
            return None

    def get_all_smm_prices(self, order_by: str = 'price_date', order: str = 'DESC') -> List[SMMPrice]:
        """获取所有SMM价格记录"""
        query = f'SELECT * FROM smm_prices ORDER BY {order_by} {order}'
        with self.get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [self._row_to_smm_price(row) for row in rows]

    def update_smm_price(self, smm_price: SMMPrice) -> bool:
        """更新SMM价格记录"""
        with self.get_connection() as conn:
            conn.execute('''
                UPDATE smm_prices SET
                    price_date = ?, highest_price = ?, lowest_price = ?,
                    average_price = ?, updated_at = ?
                WHERE id = ?
            ''', (
                smm_price.price_date, smm_price.highest_price,
                smm_price.lowest_price, smm_price.average_price,
                smm_price.updated_at, smm_price.id
            ))
            return conn.total_changes > 0

    def delete_smm_price(self, price_id: int) -> bool:
        """删除SMM价格记录"""
        with self.get_connection() as conn:
            conn.execute('DELETE FROM smm_prices WHERE id = ?', (price_id,))
            return conn.total_changes > 0

    def get_latest_smm_price(self) -> Optional[SMMPrice]:
        """获取最新的SMM月均价"""
        with self.get_connection() as conn:
            row = conn.execute('SELECT * FROM smm_prices ORDER BY price_date DESC LIMIT 1').fetchone()
            if row:
                return self._row_to_smm_price(row)
            return None

    def get_smm_price_by_date(self, date: str) -> Optional[SMMPrice]:
        """根据日期查找SMM价格（查找当天或最近之前的）"""
        with self.get_connection() as conn:
            # 先尝试查找精确匹配的日期
            row = conn.execute('SELECT * FROM smm_prices WHERE price_date <= ? ORDER BY price_date DESC LIMIT 1', (date,)).fetchone()
            if row:
                return self._row_to_smm_price(row)
            return None

    def get_monthly_smm_average(self) -> float:
        """计算SMM月度平均价格"""
        with self.get_connection() as conn:
            row = conn.execute('SELECT AVG(average_price) as avg_price FROM smm_prices').fetchone()
            return row[0] if row and row[0] else 0.0

    def get_smm_prices_by_date_range(self, start_date: str, end_date: str) -> List[SMMPrice]:
        """获取指定日期范围的SMM价格"""
        with self.get_connection() as conn:
            rows = conn.execute(
                'SELECT * FROM smm_prices WHERE price_date BETWEEN ? AND ? ORDER BY price_date ASC',
                (start_date, end_date)
            ).fetchall()
            return [self._row_to_smm_price(row) for row in rows]

    def get_smm_prices_by_month(self, year: int, month: int) -> List[SMMPrice]:
        """获取指定年月的SMM价格"""
        month_str = f"{year}-{month:02d}"
        with self.get_connection() as conn:
            rows = conn.execute(
                'SELECT * FROM smm_prices WHERE price_date LIKE ? ORDER BY price_date ASC',
                (f"{month_str}%",)
            ).fetchall()
            return [self._row_to_smm_price(row) for row in rows]

    def get_available_smm_months(self) -> List[str]:
        """获取所有可用的年月列表（格式: YYYY-MM）"""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT DISTINCT substr(price_date, 1, 7) as month FROM smm_prices ORDER BY month DESC"
            ).fetchall()
            return [row['month'] for row in rows]

    def _row_to_smm_price(self, row) -> SMMPrice:
        """将数据库行转换为SMMPrice对象"""
        return SMMPrice(
            id=row['id'],
            price_date=row['price_date'],
            highest_price=row['highest_price'],
            lowest_price=row['lowest_price'],
            average_price=row['average_price'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

    # ==================== 期货价格管理 ====================

    def create_futures_price(self, futures_price: FuturesPrice) -> int:
        """创建期货价格记录"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO futures_prices (
                    price_date, highest_price, lowest_price, average_price,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                futures_price.price_date, futures_price.highest_price,
                futures_price.lowest_price, futures_price.average_price,
                futures_price.created_at, futures_price.updated_at
            ))
            return cursor.lastrowid

    def get_futures_price(self, price_id: int) -> Optional[FuturesPrice]:
        """获取单条期货价格记录"""
        with self.get_connection() as conn:
            row = conn.execute('SELECT * FROM futures_prices WHERE id = ?', (price_id,)).fetchone()
            if row:
                return self._row_to_futures_price(row)
            return None

    def get_all_futures_prices(self, order_by: str = 'price_date', order: str = 'DESC') -> List[FuturesPrice]:
        """获取所有期货价格记录"""
        query = f'SELECT * FROM futures_prices ORDER BY {order_by} {order}'
        with self.get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [self._row_to_futures_price(row) for row in rows]

    def update_futures_price(self, futures_price: FuturesPrice) -> bool:
        """更新期货价格记录"""
        with self.get_connection() as conn:
            conn.execute('''
                UPDATE futures_prices SET
                    price_date = ?, highest_price = ?, lowest_price = ?,
                    average_price = ?, updated_at = ?
                WHERE id = ?
            ''', (
                futures_price.price_date, futures_price.highest_price,
                futures_price.lowest_price, futures_price.average_price,
                futures_price.updated_at, futures_price.id
            ))
            return conn.total_changes > 0

    def delete_futures_price(self, price_id: int) -> bool:
        """删除期货价格记录"""
        with self.get_connection() as conn:
            conn.execute('DELETE FROM futures_prices WHERE id = ?', (price_id,))
            return conn.total_changes > 0

    def get_futures_prices_by_date_range(self, start_date: str, end_date: str) -> List[FuturesPrice]:
        """获取指定日期范围的期货价格"""
        with self.get_connection() as conn:
            rows = conn.execute(
                'SELECT * FROM futures_prices WHERE price_date BETWEEN ? AND ? ORDER BY price_date ASC',
                (start_date, end_date)
            ).fetchall()
            return [self._row_to_futures_price(row) for row in rows]

    def _row_to_futures_price(self, row) -> FuturesPrice:
        """将数据库行转换为FuturesPrice对象"""
        return FuturesPrice(
            id=row['id'],
            price_date=row['price_date'],
            highest_price=row['highest_price'],
            lowest_price=row['lowest_price'],
            average_price=row['average_price'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

    # ==================== 品种管理 ====================

    def create_product(self, product: Product) -> int:
        """创建品种记录"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO products (
                    name, exchange, created_at, updated_at
                ) VALUES (?, ?, ?, ?)
            ''', (
                product.name, product.exchange, product.created_at, product.updated_at
            ))
            return cursor.lastrowid

    def get_product(self, product_id: int) -> Optional[Product]:
        """获取单条品种记录"""
        with self.get_connection() as conn:
            row = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
            if row:
                return self._row_to_product(row)
            return None

    def get_all_products(self) -> List[Product]:
        """获取所有品种记录"""
        with self.get_connection() as conn:
            rows = conn.execute('SELECT * FROM products ORDER BY name ASC').fetchall()
            return [self._row_to_product(row) for row in rows]

    def get_product_by_name(self, name: str) -> Optional[Product]:
        """根据名称获取品种"""
        with self.get_connection() as conn:
            row = conn.execute('SELECT * FROM products WHERE name = ?', (name,)).fetchone()
            if row:
                return self._row_to_product(row)
            return None

    def update_product(self, product: Product) -> bool:
        """更新品种记录"""
        with self.get_connection() as conn:
            conn.execute('''
                UPDATE products SET
                    name = ?, exchange = ?, updated_at = ?
                WHERE id = ?
            ''', (
                product.name, product.exchange, product.updated_at, product.id
            ))
            return conn.total_changes > 0

    def delete_product(self, product_id: int) -> bool:
        """删除品种记录"""
        with self.get_connection() as conn:
            conn.execute('DELETE FROM products WHERE id = ?', (product_id,))
            return conn.total_changes > 0

    def _row_to_product(self, row) -> Product:
        """将数据库行转换为Product对象"""
        return Product(
            id=row['id'],
            name=row['name'],
            exchange=row['exchange'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

    def _row_to_trade(self, row) -> Trade:
        """将数据库行转换为Trade对象"""
        # 处理可能不存在的新字段
        supplier = row['supplier'] if 'supplier' in row.keys() else None
        settlement_price = row['settlement_price'] if 'settlement_price' in row.keys() else None
        premium = row['premium'] if 'premium' in row.keys() else None
        physical_tons = row['physical_tons'] if 'physical_tons' in row.keys() else None
        related_po = row['related_po'] if 'related_po' in row.keys() else None

        return Trade(
            id=row['id'],
            trade_date=row['trade_date'],
            exchange=row['exchange'],
            product_name=row['product_name'],
            contract=row['contract'],
            direction=row['direction'],
            entry_price=row['entry_price'],
            quantity=row['quantity'],
            supplier=supplier,
            settlement_price=settlement_price,
            premium=premium,
            physical_tons=physical_tons,
            related_po=related_po,
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
        )


# 全局数据库实例
db = DatabaseManager()
