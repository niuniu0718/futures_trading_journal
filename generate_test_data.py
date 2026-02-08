"""
生成测试数据脚本
生成2025年1月30日到今天的交易记录
"""
import random
from datetime import datetime, timedelta
from database import db
from models import Trade

# 配置参数
START_DATE = datetime(2025, 1, 30)
END_DATE = datetime.now()
PRODUCTS = ['工碳', '电碳']
CONTRACTS = ['LC2505', 'LC2506', 'LC2507', 'LC2509', 'LC2512']
DIRECTIONS = ['long', 'short']
SUPPLIERS = ['供应商A', '供应商B', '供应商C', None, None]  # 60%没有供应商

# 价格范围（元/吨）
PRICE_RANGE = (115000, 135000)

def generate_random_date(start, end):
    """生成随机日期"""
    delta = end - start
    random_days = random.randint(0, delta.days)
    return start + timedelta(days=random_days)

def generate_test_data(num_trades=50):
    """生成测试交易数据"""
    print(f"开始生成 {num_trades} 条测试数据...")

    created_count = 0
    for i in range(num_trades):
        try:
            # 随机生成基础数据
            trade_date = generate_random_date(START_DATE, END_DATE).strftime('%Y-%m-%d')
            product_name = random.choice(PRODUCTS)
            contract = random.choice(CONTRACTS)
            direction = random.choice(DIRECTIONS)
            entry_price = random.randint(*PRICE_RANGE) + random.randint(-1000, 1000)
            quantity = random.randint(1, 50)
            supplier = random.choice(SUPPLIERS)

            # 计算实物吨
            physical_tons = round(quantity * 1.13)

            # 如果有供应商，生成结算价和贴水
            if supplier:
                settlement_price = entry_price + random.randint(-2000, 2000)
                premium = settlement_price - entry_price
            else:
                settlement_price = None
                premium = None

            # 30%的交易是已平仓的
            is_closed = random.random() < 0.3

            if is_closed:
                # 生成平仓数据
                exit_days_after = random.randint(1, 30)
                exit_date_obj = datetime.strptime(trade_date, '%Y-%m-%d') + timedelta(days=exit_days_after)
                exit_date = exit_date_obj.strftime('%Y-%m-%d')

                # 平仓价格（随机涨跌）
                price_change = random.randint(-5000, 5000)
                exit_price = entry_price + price_change

                status = 'closed'
            else:
                exit_date = None
                exit_price = None
                status = 'open'

            # 创建交易记录
            trade = Trade(
                trade_date=trade_date,
                exchange='gfex',
                product_name=product_name,
                contract=contract,
                direction=direction,
                entry_price=float(entry_price),
                quantity=float(quantity),
                supplier=supplier,
                settlement_price=float(settlement_price) if settlement_price else None,
                premium=float(premium) if premium else None,
                physical_tons=float(physical_tons),
                related_po=f"PO{random.randint(1000, 9999)}" if random.random() < 0.4 else None,
                stop_loss=None,
                take_profit=None,
                exit_price=float(exit_price) if exit_price else None,
                exit_date=exit_date,
                fee=random.uniform(10, 100),
                profit_loss=0.0,
                status=status,
                ma5=None,
                ma10=None,
                ma20=None,
                rsi=None,
                macd=None,
                entry_reason=None,
                market_trend=None,
                notes=f"测试数据 {i+1}"
            )

            # 如果已平仓，计算盈亏
            if trade.exit_price:
                trade.calculate_profit_loss()

            # 保存到数据库
            db.create_trade(trade)
            created_count += 1

            if (i + 1) % 10 == 0:
                print(f"已生成 {i + 1}/{num_trades} 条数据...")

        except Exception as e:
            print(f"生成第 {i+1} 条数据时出错: {e}")
            continue

    print(f"\n完成！成功生成 {created_count} 条测试数据")
    print(f"日期范围: {START_DATE.strftime('%Y-%m-%d')} ~ {END_DATE.strftime('%Y-%m-%d')}")

if __name__ == '__main__':
    generate_test_data(50)
