"""
数据库迁移模块
提供版本化的数据库结构迁移功能
"""
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Callable, Any
from loguru import logger
from config import DATABASE_PATH


class Migration:
    """数据库迁移基类"""

    def __init__(self, version: int, description: str):
        self.version = version
        self.description = description

    def up(self, conn: sqlite3.Connection):
        """执行迁移：由旧版本升级到新版本"""
        raise NotImplementedError

    def down(self, conn: sqlite3.Connection):
        """回滚迁移：由新版本降级到旧版本（可选）"""
        raise NotImplementedError


class Migration001_AddSupplierFields(Migration):
    """添加供应商相关字段（settlement_price, premium, physical_tons, related_po）"""

    def __init__(self):
        super().__init__(1, "添加供应商相关字段")

    def up(self, conn: sqlite3.Connection):
        """添加新字段"""
        cursor = conn.execute("PRAGMA table_info(trades)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'supplier' not in columns:
            conn.execute('ALTER TABLE trades ADD COLUMN supplier TEXT')
            logger.info("添加列: supplier")

        if 'settlement_price' not in columns:
            conn.execute('ALTER TABLE trades ADD COLUMN settlement_price REAL')
            logger.info("添加列: settlement_price")

        if 'premium' not in columns:
            conn.execute('ALTER TABLE trades ADD COLUMN premium REAL')
            logger.info("添加列: premium")

        if 'physical_tons' not in columns:
            conn.execute('ALTER TABLE trades ADD COLUMN physical_tons REAL')
            logger.info("添加列: physical_tons")

        if 'related_po' not in columns:
            conn.execute('ALTER TABLE trades ADD COLUMN related_po TEXT')
            logger.info("添加列: related_po")

    def down(self, conn: sqlite3.Connection):
        """SQLite不支持删除列，需要重建表"""
        # 创建临时表（不含新字段）
        conn.execute('''
            CREATE TABLE trades_temp (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_date TEXT NOT NULL,
                exchange TEXT NOT NULL,
                product_name TEXT NOT NULL,
                contract TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                quantity REAL NOT NULL,
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

        # 复制数据（排除新字段）
        conn.execute('''
            INSERT INTO trades_temp (
                id, trade_date, exchange, product_name, contract, direction,
                entry_price, quantity, stop_loss, take_profit, exit_price,
                exit_date, fee, profit_loss, status, ma5, ma10, ma20,
                rsi, macd, entry_reason, market_trend, notes,
                created_at, updated_at
            )
            SELECT
                id, trade_date, exchange, product_name, contract, direction,
                entry_price, quantity, stop_loss, take_profit, exit_price,
                exit_date, fee, profit_loss, status, ma5, ma10, ma20,
                rsi, macd, entry_reason, market_trend, notes,
                created_at, updated_at
            FROM trades
        ''')

        # 删除旧表，重命名新表
        conn.execute('DROP TABLE trades')
        conn.execute('ALTER TABLE trades_temp RENAME TO trades')


class Migration002_AddBillingTable(Migration):
    """添加账务核销表"""

    def __init__(self):
        super().__init__(2, "添加账务核销表")

    def up(self, conn: sqlite3.Connection):
        """创建账务核销表"""
        # 先检查表是否存在且使用旧的列名
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='billing_records'")
        table_exists = cursor.fetchone()

        if table_exists:
            # 检查是否有 billing_date 列
            cursor = conn.execute("PRAGMA table_info(billing_records)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'billing_date' in columns and 'billing_month' not in columns:
                # 重命名列
                conn.execute('ALTER TABLE billing_records RENAME TO billing_records_old')
                logger.info("重命名表: billing_records -> billing_records_old")

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
                related_po TEXT,
                notes TEXT,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (trade_id) REFERENCES trades(id) ON DELETE CASCADE,
                UNIQUE(trade_id)
            )
        ''')

        # 如果有旧表，迁移数据
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='billing_records_old'")
        if cursor.fetchone():
            conn.execute('''
                INSERT INTO billing_records (
                    id, trade_id, billing_month, base_month, base_price,
                    settlement_price, quantity, physical_tons,
                    settlement_amount, discount, notes, created_at, updated_at
                )
                SELECT
                    id, trade_id, billing_date, base_month, base_price,
                    settlement_price, quantity, physical_tons,
                    settlement_amount, discount, notes, created_at, updated_at
                FROM billing_records_old
            ''')
            conn.execute('DROP TABLE billing_records_old')
            logger.info("迁移旧数据并删除旧表")

        logger.info("创建表: billing_records")

    def down(self, conn: sqlite3.Connection):
        """删除账务核销表"""
        conn.execute('DROP TABLE IF EXISTS billing_records')
        logger.info("删除表: billing_records")


class MigrationManager:
    """数据库迁移管理器"""

    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self.migrations: Dict[int, Migration] = {}
        self._register_migrations()

    def _register_migrations(self):
        """注册所有迁移"""
        self.migrations[1] = Migration001_AddSupplierFields()
        self.migrations[2] = Migration002_AddBillingTable()
        # 在这里添加新的迁移
        # self.migrations[3] = Migration003_AddNewFeature()

    def _init_schema_version(self, conn: sqlite3.Connection):
        """初始化版本表"""
        conn.execute('''
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                description TEXT,
                applied_at TEXT,
                execution_time INTEGER
            )
        ''')

    def get_current_version(self) -> int:
        """获取当前数据库版本"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
            )
            if not cursor.fetchone():
                return 0

            cursor = conn.execute('SELECT MAX(version) FROM schema_version')
            result = cursor.fetchone()
            return result[0] if result and result[0] else 0
        finally:
            conn.close()

    def get_applied_migrations(self) -> List[Dict[str, Any]]:
        """获取已应用的迁移列表"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
            )
            if not cursor.fetchone():
                return []

            cursor = conn.execute('SELECT version, description, applied_at FROM schema_version ORDER BY version')
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_pending_migrations(self) -> List[Migration]:
        """获取待执行的迁移"""
        current_version = self.get_current_version()
        pending = []

        for version, migration in sorted(self.migrations.items()):
            if version > current_version:
                pending.append(migration)

        return pending

    def migrate(self, target_version: int = None) -> bool:
        """
        执行数据库迁移

        Args:
            target_version: 目标版本，None表示迁移到最新版本

        Returns:
            bool: 迁移是否成功
        """
        current_version = self.get_current_version()
        latest_version = max(self.migrations.keys()) if self.migrations else 0

        if target_version is None:
            target_version = latest_version

        if target_version <= current_version:
            logger.info(f"数据库已是最新版本 (v{current_version})")
            return True

        if target_version > latest_version:
            logger.warning(f"目标版本 v{target_version} 不存在，最新版本为 v{latest_version}")
            target_version = latest_version

        logger.info(f"开始迁移数据库: v{current_version} -> v{target_version}")

        try:
            conn = sqlite3.connect(self.db_path)
            self._init_schema_version(conn)

            # 按顺序执行迁移
            for version in range(current_version + 1, target_version + 1):
                if version not in self.migrations:
                    logger.warning(f"版本 v{version} 的迁移不存在，跳过")
                    continue

                migration = self.migrations[version]
                logger.info(f"执行迁移 v{version}: {migration.description}")

                start_time = datetime.now()
                migration.up(conn)

                # 记录迁移历史
                execution_time = (datetime.now() - start_time).total_seconds()
                conn.execute('''
                    INSERT INTO schema_version (version, description, applied_at, execution_time)
                    VALUES (?, ?, ?, ?)
                ''', (version, migration.description, datetime.now().isoformat(), execution_time))

                conn.commit()
                logger.info(f"迁移 v{version} 完成 (耗时: {execution_time:.2f}秒)")

            conn.close()
            logger.info(f"数据库迁移完成: v{current_version} -> v{target_version}")
            return True

        except Exception as e:
            logger.error(f"数据库迁移失败: {e}")
            return False

    def rollback(self, target_version: int) -> bool:
        """
        回滚数据库到指定版本

        Args:
            target_version: 目标版本

        Returns:
            bool: 回滚是否成功
        """
        current_version = self.get_current_version()

        if target_version >= current_version:
            logger.warning(f"当前版本 v{current_version} 已经是 v{target_version} 或更高")
            return False

        logger.info(f"开始回滚数据库: v{current_version} -> v{target_version}")

        try:
            conn = sqlite3.connect(self.db_path)

            # 反向执行回滚
            for version in range(current_version, target_version, -1):
                if version not in self.migrations:
                    logger.warning(f"版本 v{version} 的迁移不存在，跳过")
                    continue

                migration = self.migrations[version]
                logger.info(f"回滚迁移 v{version}: {migration.description}")

                migration.down(conn)

                # 删除迁移记录
                conn.execute('DELETE FROM schema_version WHERE version = ?', (version,))
                conn.commit()

                logger.info(f"回滚 v{version} 完成")

            conn.close()
            logger.info(f"数据库回滚完成: v{current_version} -> v{target_version}")
            return True

        except Exception as e:
            logger.error(f"数据库回滚失败: {e}")
            return False

    def status(self) -> Dict[str, Any]:
        """获取迁移状态信息"""
        current_version = self.get_current_version()
        latest_version = max(self.migrations.keys()) if self.migrations else 0
        pending = self.get_pending_migrations()
        applied = self.get_applied_migrations()

        return {
            'current_version': current_version,
            'latest_version': latest_version,
            'needs_migration': current_version < latest_version,
            'pending_count': len(pending),
            'pending_migrations': [{'version': m.version, 'description': m.description} for m in pending],
            'applied_migrations': applied
        }


# 创建全局迁移管理器实例
migration_manager = MigrationManager()


def migrate_database() -> bool:
    """便捷函数：执行数据库迁移到最新版本"""
    return migration_manager.migrate()


if __name__ == '__main__':
    # 命令行工具
    import sys

    manager = MigrationManager()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == 'status':
            status = manager.status()
            print("\n=== 数据库迁移状态 ===")
            print(f"当前版本: v{status['current_version']}")
            print(f"最新版本: v{status['latest_version']}")
            print(f"需要迁移: {'是' if status['needs_migration'] else '否'}")

            if status['applied_migrations']:
                print("\n已应用的迁移:")
                for m in status['applied_migrations']:
                    print(f"  - v{m['version']}: {m['description']} ({m['applied_at']})")

            if status['pending_migrations']:
                print("\n待执行的迁移:")
                for m in status['pending_migrations']:
                    print(f"  - v{m['version']}: {m['description']}")

        elif command == 'migrate':
            target = int(sys.argv[2]) if len(sys.argv) > 2 else None
            success = manager.migrate(target)
            sys.exit(0 if success else 1)

        elif command == 'rollback':
            target = int(sys.argv[2])
            success = manager.rollback(target)
            sys.exit(0 if success else 1)

        else:
            print("用法:")
            print("  python migrations.py status      - 查看迁移状态")
            print("  python migrations.py migrate    - 执行迁移到最新版本")
            print("  python migrations.py migrate 2  - 迁移到指定版本")
            print("  python migrations.py rollback 1 - 回滚到指定版本")
    else:
        print("用法:")
        print("  python migrations.py status      - 查看迁移状态")
        print("  python migrations.py migrate    - 执行迁移到最新版本")
        print("  python migrations.py migrate 2  - 迁移到指定版本")
        print("  python migrations.py rollback 1 - 回滚到指定版本")
