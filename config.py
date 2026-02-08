"""
配置文件
"""
import os

# 项目路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
EXPORTS_DIR = os.path.join(BASE_DIR, 'exports')

# 确保目录存在
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)

# 数据库路径
DATABASE_PATH = os.path.join(DATA_DIR, 'trading_journal.db')

# Flask 配置
SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
DEBUG = False

# 日志配置
# 可选值: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
# 设置为 "WARNING" 或更高可以减少控制台输出
LOG_LEVEL = "WARNING"

# 交易所配置
EXCHANGES = {
    'gfex': '广期所',
    'shfe': '上期所',
    'dce': '大商所',
    'czce': '郑商所',
    'cffe': '中金所'
}

# 方向配置
DIRECTIONS = {
    'long': '多单',
    'short': '空单'
}

# 状态配置
STATUSES = {
    'open': '持仓中',
    'closed': '已平仓'
}

# 走势配置
TRENDS = {
    'uptrend': '上涨',
    'downtrend': '下跌',
    'neutral': '震荡'
}

# SMM月均价配置（碳酸锂）
# 可以手动更新这个价格，单位：元/吨
SMM_MONTHLY_PRICE = 155125.0  # 示例价格，可根据实际情况修改

# 分页配置
TRADES_PER_PAGE = 20
