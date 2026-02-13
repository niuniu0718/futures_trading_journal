"""
数据同步模块
提供数据导出、导入和同步功能
"""
import os
import json
import sqlite3
import shutil
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger
from config import DATABASE_PATH, EXPORTS_DIR
from migrations import MigrationManager


class DataExporter:
    """数据导出器"""

    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self.migration_manager = MigrationManager(db_path)

    def export_full(self, output_path: Optional[str] = None) -> str:
        """
        导出完整数据（包含数据库文件和元数据）

        Args:
            output_path: 输出文件路径，None则自动生成

        Returns:
            导出文件的路径
        """
        # 生成导出文件名
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(EXPORTS_DIR, f'trading_journal_backup_{timestamp}.json')

        # 获取当前数据库版本
        status = self.migration_manager.status()
        schema_version = status['current_version']

        # 导出所有表的数据
        data = {
            'version': 1,  # 导出格式版本
            'schema_version': schema_version,  # 数据库结构版本
            'export_date': datetime.now().isoformat(),
            'tables': {}
        }

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        try:
            # 获取所有表名
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            tables = [row[0] for row in cursor.fetchall()]

            for table_name in tables:
                # 获取表结构
                cursor = conn.execute(f'PRAGMA table_info({table_name})')
                columns = [row[1] for row in cursor.fetchall()]

                # 获取表数据
                cursor = conn.execute(f'SELECT * FROM {table_name}')
                rows = cursor.fetchall()

                # 转换为可序列化的格式
                data['tables'][table_name] = {
                    'columns': columns,
                    'rows': [dict(row) for row in rows]
                }

                logger.info(f"导出表 {table_name}: {len(rows)} 行")

        finally:
            conn.close()

        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"完整数据导出到: {output_path}")
        return output_path

    def export_database(self, output_path: Optional[str] = None) -> str:
        """
        直接导出数据库文件（最快的方式）

        Args:
            output_path: 输出文件路径，None则自动生成

        Returns:
            导出文件的路径
        """
        # 生成导出文件名
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(EXPORTS_DIR, f'trading_journal_db_{timestamp}.db')

        # 获取当前数据库版本
        status = self.migration_manager.status()

        # 复制数据库文件
        shutil.copy2(self.db_path, output_path)

        # 创建元数据文件
        meta_path = output_path.replace('.db', '_meta.json')
        meta = {
            'schema_version': status['current_version'],
            'export_date': datetime.now().isoformat(),
            'original_db_path': self.db_path
        }

        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        logger.info(f"数据库文件导出到: {output_path}")
        logger.info(f"元数据文件导出到: {meta_path}")
        return output_path


class DataImporter:
    """数据导入器"""

    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self.migration_manager = MigrationManager(db_path)

    def import_full(self, input_path: str, merge: bool = False) -> bool:
        """
        导入完整数据

        Args:
            input_path: 导入文件路径（JSON格式）
            merge: 是否合并数据（True保留现有数据，False覆盖）

        Returns:
            导入是否成功
        """
        if not os.path.exists(input_path):
            logger.error(f"导入文件不存在: {input_path}")
            return False

        # 读取导入文件
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        schema_version = data.get('schema_version', 0)
        export_date = data.get('export_date', '')
        tables = data.get('tables', {})

        logger.info(f"从文件导入数据: {input_path}")
        logger.info(f"导出时间: {export_date}")
        logger.info(f"数据版本: v{schema_version}")

        # 检查当前数据库版本
        current_status = self.migration_manager.status()
        current_version = current_status['current_version']
        latest_version = current_status['latest_version']

        if current_version > schema_version:
            logger.warning(f"当前数据库版本 v{current_version} 高于导入数据版本 v{schema_version}")
            logger.warning("导入后可能需要重新执行迁移")

        # 备份当前数据库
        if not merge:
            backup_path = self._backup_current_db()
            logger.info(f"已备份当前数据库到: {backup_path}")

        # 如果不是合并模式，清空数据库
        if not merge:
            self._clear_database()

        # 导入数据
        conn = sqlite3.connect(self.db_path)

        try:
            for table_name, table_data in tables.items():
                columns = table_data['columns']
                rows = table_data['rows']

                if not rows:
                    continue

                # 确保表存在（由迁移系统创建）
                self._ensure_table_exists(conn, table_name, columns)

                # 插入数据
                placeholders = ', '.join(['?' for _ in columns])
                column_names = ', '.join(columns)

                for row in rows:
                    values = [row.get(col) for col in columns]
                    try:
                        conn.execute(
                            f'INSERT OR REPLACE INTO {table_name} ({column_names}) VALUES ({placeholders})',
                            values
                        )
                    except sqlite3.Error as e:
                        logger.warning(f"插入行失败 ({table_name}): {e}")
                        if merge:
                            # 合并模式下，尝试忽略冲突
                            try:
                                conn.execute(
                                    f'INSERT OR IGNORE INTO {table_name} ({column_names}) VALUES ({placeholders})',
                                    values
                                )
                            except:
                                pass

                logger.info(f"导入表 {table_name}: {len(rows)} 行")

            conn.commit()

        except Exception as e:
            conn.rollback()
            logger.error(f"导入数据失败: {e}")
            if not merge and backup_path:
                logger.info(f"恢复备份: {backup_path}")
                shutil.copy2(backup_path, self.db_path)
            return False

        finally:
            conn.close()

        # 执行迁移到最新版本
        if schema_version < latest_version:
            logger.info(f"执行数据库迁移: v{schema_version} -> v{latest_version}")
            if self.migration_manager.migrate():
                logger.info("数据库迁移完成")
            else:
                logger.error("数据库迁移失败")
                return False

        logger.info("数据导入完成")
        return True

    def import_database(self, input_path: str, backup: bool = True) -> bool:
        """
        直接导入数据库文件（最快的方式）

        Args:
            input_path: 导入文件路径（.db文件）
            backup: 是否备份当前数据库

        Returns:
            导入是否成功
        """
        if not os.path.exists(input_path):
            logger.error(f"导入文件不存在: {input_path}")
            return False

        # 检查元数据文件
        meta_path = input_path.replace('.db', '_meta.json')
        schema_version = 0

        if os.path.exists(meta_path):
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
                schema_version = meta.get('schema_version', 0)
                export_date = meta.get('export_date', '')
                logger.info(f"导入数据库版本: v{schema_version}")
                logger.info(f"导出时间: {export_date}")

        # 备份当前数据库
        if backup:
            backup_path = self._backup_current_db()
            logger.info(f"已备份当前数据库到: {backup_path}")

        try:
            # 复制数据库文件
            shutil.copy2(input_path, self.db_path)
            logger.info(f"数据库文件导入完成: {self.db_path}")

            # 执行迁移到最新版本
            latest_version = self.migration_manager.status()['latest_version']
            if schema_version < latest_version:
                logger.info(f"执行数据库迁移: v{schema_version} -> v{latest_version}")
                if self.migration_manager.migrate():
                    logger.info("数据库迁移完成")
                else:
                    logger.error("数据库迁移失败")
                    return False

            return True

        except Exception as e:
            logger.error(f"导入数据库失败: {e}")
            if backup:
                logger.info(f"恢复备份: {backup_path}")
                shutil.copy2(backup_path, self.db_path)
            return False

    def _backup_current_db(self) -> str:
        """备份当前数据库"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(EXPORTS_DIR, f'backup_before_import_{timestamp}.db')
        shutil.copy2(self.db_path, backup_path)
        return backup_path

    def _clear_database(self):
        """清空数据库（删除所有数据但保留表结构）"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            tables = [row[0] for row in cursor.fetchall()]

            for table_name in tables:
                conn.execute(f'DELETE FROM {table_name}')

            conn.commit()
            logger.info("数据库已清空")
        finally:
            conn.close()

    def _ensure_table_exists(self, conn: sqlite3.Connection, table_name: str, columns: list):
        """确保表存在"""
        cursor = conn.execute(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
        )
        if not cursor.fetchone():
            logger.warning(f"表 {table_name} 不存在，可能需要先执行迁移")
            # 表应该由迁移系统创建，这里不处理


def export_data(format: str = 'db') -> str:
    """
    便捷函数：导出数据

    Args:
        format: 导出格式 ('db' 或 'json')

    Returns:
        导出文件路径
    """
    exporter = DataExporter()

    if format == 'db':
        return exporter.export_database()
    else:
        return exporter.export_full()


def import_data(input_path: str, merge: bool = False, backup: bool = True) -> bool:
    """
    便捷函数：导入数据

    Args:
        input_path: 导入文件路径
        merge: 是否合并数据（仅JSON格式支持）
        backup: 是否备份当前数据库

    Returns:
        导入是否成功
    """
    importer = DataImporter()

    if input_path.endswith('.db'):
        return importer.import_database(input_path, backup=backup)
    else:
        return importer.import_full(input_path, merge=merge)


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == 'export':
            format_type = sys.argv[2] if len(sys.argv) > 2 else 'db'
            path = export_data(format_type)
            print(f"导出完成: {path}")

        elif command == 'import':
            if len(sys.argv) > 2:
                input_file = sys.argv[2]
                merge = '--merge' in sys.argv
                no_backup = '--no-backup' in sys.argv
                success = import_data(input_file, merge=merge, backup=not no_backup)
                print(f"导入{'成功' if success else '失败'}")
                sys.exit(0 if success else 1)
            else:
                print("用法: python data_sync.py import <文件路径> [--merge] [--no-backup]")

        else:
            print("用法:")
            print("  python data_sync.py export [db|json]  - 导出数据")
            print("  python data_sync.py import <文件>     - 导入数据（覆盖）")
            print("  python data_sync.py import <文件> --merge  - 导入数据（合并）")
    else:
        print("用法:")
        print("  python data_sync.py export [db|json]  - 导出数据")
        print("  python data_sync.py import <文件>     - 导入数据（覆盖）")
        print("  python data_sync.py import <文件> --merge  - 导入数据（合并）")
