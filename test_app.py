#!/usr/bin/env python3
"""
测试脚本 - 验证期货交易记录系统功能
"""
import sqlite3
import requests
import time
import json

BASE_URL = "http://localhost:5000"


def test_database():
    """测试数据库连接"""
    print("🔍 测试数据库连接...")
    try:
        conn = sqlite3.connect('data/trading_journal.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"✅ 数据库连接成功，表: {tables}")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False


def test_pages():
    """测试页面访问"""
    print("\n🔍 测试页面访问...")
    pages = [
        ("/", "首页"),
        ("/trades", "交易记录"),
        ("/statistics", "统计分析")
    ]

    for path, name in pages:
        try:
            response = requests.get(f"{BASE_URL}{path}")
            if response.status_code == 200:
                print(f"✅ {name} ({path}): {response.status_code}")
            else:
                print(f"❌ {name} ({path}): {response.status_code}")
        except Exception as e:
            print(f"❌ {name} ({path}): 错误 - {e}")


def test_api():
    """测试API接口"""
    print("\n🔍 测试API接口...")
    apis = [
        ("/api/trades", "交易数据API"),
        ("/api/statistics", "统计数据API")
    ]

    for path, name in apis:
        try:
            response = requests.get(f"{BASE_URL}{path}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {name} ({path}): {response.status_code}")
                print(f"   数据: {json.dumps(data, ensure_ascii=False, indent=2)[:100]}...")
            else:
                print(f"❌ {name} ({path}): {response.status_code}")
        except Exception as e:
            print(f"❌ {name} ({path}): 错误 - {e}")


def test_create_trade():
    """测试创建交易记录"""
    print("\n🔍 测试创建交易记录...")
    trade_data = {
        'trade_date': '2024-02-01',
        'exchange': 'gfex',
        'product_name': '碳酸锂',
        'contract': 'LC2405',
        'direction': 'long',
        'entry_price': '125000',
        'quantity': '10',
        'stop_loss': '123000',
        'take_profit': '128000',
        'fee': '50',
        'ma5': '124000',
        'ma10': '123500',
        'ma20': '123000',
        'rsi': '55',
        'macd': '100',
        'market_trend': 'uptrend',
        'entry_reason': '突破前高',
        'notes': '测试交易记录'
    }

    try:
        response = requests.post(f"{BASE_URL}/trades/new", data=trade_data)
        if response.status_code == 200:
            print("✅ 交易记录创建成功")
            return True
        else:
            print(f"❌ 交易记录创建失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 交易记录创建错误: {e}")
        return False


def test_close_trade():
    """测试平仓操作"""
    print("\n🔍 测试平仓操作...")
    # 获取第一条记录
    try:
        response = requests.get(f"{BASE_URL}/api/trades")
        trades = response.json()
        if trades and len(trades) > 0:
            trade_id = trades[0]['id']
            close_data = {
                'exit_price': '127000',
                'exit_date': '2024-02-02'
            }
            response = requests.post(f"{BASE_URL}/trades/{trade_id}/close", data=close_data)
            if response.status_code == 200:
                print(f"✅ 交易记录平仓成功 (ID: {trade_id})")
                return True
            else:
                print(f"❌ 交易记录平仓失败: {response.status_code}")
                return False
        else:
            print("⚠️  没有找到可平仓的交易记录")
            return False
    except Exception as e:
        print(f"❌ 交易记录平仓错误: {e}")
        return False


def test_statistics():
    """测试统计数据"""
    print("\n🔍 测试统计数据...")
    try:
        response = requests.get(f"{BASE_URL}/api/statistics")
        stats = response.json()

        print("✅ 基础统计:")
        basic = stats['basic']
        print(f"   总交易数: {basic['total_trades']}")
        print(f"   已平仓: {basic['closed_trades']}")
        print(f"   总盈亏: {basic['total_profit_loss']}")
        print(f"   胜率: {basic['win_rate']}%")

        if basic['total_trades'] > 0:
            print("✅ 统计数据正常")
            return True
        else:
            print("⚠️  暂无交易数据")
            return True
    except Exception as e:
        print(f"❌ 统计数据错误: {e}")
        return False


def test_export():
    """测试导出功能"""
    print("\n🔍 测试导出功能...")
    try:
        response = requests.get(f"{BASE_URL}/export/csv")
        if response.status_code == 200:
            print(f"✅ CSV导出成功 (大小: {len(response.content)} bytes)")
            return True
        else:
            print(f"❌ CSV导出失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ CSV导出错误: {e}")
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("期货交易记录系统 - 功能测试")
    print("=" * 60)

    results = []

    # 等待服务器启动
    print("\n⏳ 等待服务器启动...")
    time.sleep(2)

    # 运行测试
    results.append(("数据库连接", test_database()))
    results.append(("页面访问", test_pages()))
    results.append(("API接口", test_api()))
    results.append(("创建交易", test_create_trade()))
    results.append(("平仓操作", test_close_trade()))
    results.append(("统计数据", test_statistics()))
    results.append(("导出功能", test_export()))

    # 测试结果汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")

    print(f"\n总计: {passed}/{total} 通过")

    if passed == total:
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")

    print("=" * 60)


if __name__ == "__main__":
    main()
