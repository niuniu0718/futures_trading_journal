"""
统计分析模块
"""
import pandas as pd
from typing import Dict, List, Any
from datetime import datetime
from database import db
from models import Trade


class TradeAnalyzer:
    """交易分析器"""

    def __init__(self):
        self.trades = self._load_trades()

    def _load_trades(self) -> pd.DataFrame:
        """加载交易数据到DataFrame"""
        trades = db.get_all_trades()
        data = [trade.to_dict() for trade in trades]
        df = pd.DataFrame(data)
        if not df.empty:
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            if 'exit_date' in df.columns:
                df['exit_date'] = pd.to_datetime(df['exit_date'], errors='coerce')
        return df

    def reload(self):
        """重新加载数据"""
        self.trades = self._load_trades()

    def get_daily_profit_loss(self) -> List[Dict[str, Any]]:
        """获取每日累计盈亏"""
        if self.trades.empty:
            return []

        closed_trades = self.trades[self.trades['status'] == 'closed'].copy()
        if closed_trades.empty:
            return []

        daily_pl = closed_trades.groupby(closed_trades['exit_date'].dt.date)['profit_loss'].sum().cumsum()
        return [
            {'date': str(date), 'cumulative_pl': round(pl, 2)}
            for date, pl in daily_pl.items()
        ]

    def get_monthly_stats(self) -> List[Dict[str, Any]]:
        """获取月度统计数据"""
        if self.trades.empty:
            return []

        closed_trades = self.trades[self.trades['status'] == 'closed'].copy()
        if closed_trades.empty:
            return []

        closed_trades['year_month'] = closed_trades['exit_date'].dt.to_period('M')
        monthly = closed_trades.groupby('year_month').agg({
            'profit_loss': 'sum',
            'id': 'count'
        }).reset_index()
        monthly.columns = ['period', 'profit_loss', 'count']
        monthly['win_rate'] = closed_trades.groupby('year_month').apply(
            lambda x: (x['profit_loss'] > 0).sum() / len(x) * 100
        ).values

        return [
            {
                'month': str(row['period']),
                'profit_loss': round(row['profit_loss'], 2),
                'count': int(row['count']),
                'win_rate': round(row['win_rate'], 2)
            }
            for _, row in monthly.iterrows()
        ]

    def get_product_performance(self) -> List[Dict[str, Any]]:
        """获取品种表现统计"""
        if self.trades.empty:
            return []

        product_stats = self.trades.groupby('product_name').agg({
            'profit_loss': 'sum',
            'id': 'count'
        }).reset_index()
        product_stats.columns = ['product', 'profit_loss', 'count']

        # 计算胜率
        win_rates = []
        for product in product_stats['product']:
            product_trades = self.trades[self.trades['product_name'] == product]
            closed = product_trades[product_trades['status'] == 'closed']
            if len(closed) > 0:
                win_rate = (closed['profit_loss'] > 0).sum() / len(closed) * 100
            else:
                win_rate = 0
            win_rates.append(win_rate)

        product_stats['win_rate'] = win_rates

        return [
            {
                'product': row['product'],
                'profit_loss': round(row['profit_loss'], 2),
                'count': int(row['count']),
                'win_rate': round(row['win_rate'], 2)
            }
            for _, row in product_stats.iterrows()
        ]

    def get_win_rate_trend(self) -> List[Dict[str, Any]]:
        """获取胜率趋势"""
        if self.trades.empty:
            return []

        closed_trades = self.trades[self.trades['status'] == 'closed'].copy()
        if closed_trades.empty:
            return []

        closed_trades = closed_trades.sort_values('exit_date')
        closed_trades['is_win'] = closed_trades['profit_loss'] > 0

        # 按每10笔交易计算滚动胜率
        window = min(10, len(closed_trades))
        rolling_win_rate = closed_trades['is_win'].rolling(window=window, min_periods=1).mean() * 100

        return [
            {
                'trade_num': i + 1,
                'win_rate': round(win_rate, 2)
            }
            for i, win_rate in enumerate(rolling_win_rate)
        ]

    def get_price_trend(self) -> Dict[str, List]:
        """获取价格趋势数据（用于图表）"""
        if self.trades.empty:
            return {'labels': [], 'entry_prices': [], 'exit_prices': []}

        closed_trades = self.trades[self.trades['status'] == 'closed'].copy()
        if closed_trades.empty:
            return {'labels': [], 'entry_prices': [], 'exit_prices': []}

        closed_trades = closed_trades.sort_values('exit_date')

        return {
            'labels': [f"{row['product_name']}\n{row['exit_date'].strftime('%Y-%m-%d')}"
                      for _, row in closed_trades.iterrows()],
            'entry_prices': closed_trades['entry_price'].tolist(),
            'exit_prices': closed_trades['exit_price'].tolist()
        }

    def get_risk_metrics(self) -> Dict[str, Any]:
        """获取风险指标"""
        if self.trades.empty:
            return {
                'max_drawdown': 0,
                'avg_profit': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'expectancy': 0
            }

        closed_trades = self.trades[self.trades['status'] == 'closed'].copy()
        if closed_trades.empty:
            return {
                'max_drawdown': 0,
                'avg_profit': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'expectancy': 0
            }

        # 计算最大回撤
        cumulative = closed_trades['profit_loss'].cumsum()
        rolling_max = cumulative.expanding().max()
        drawdown = cumulative - rolling_max
        max_drawdown = drawdown.min()

        # 平均盈利和平均亏损
        profits = closed_trades[closed_trades['profit_loss'] > 0]['profit_loss']
        losses = closed_trades[closed_trades['profit_loss'] < 0]['profit_loss']

        avg_profit = profits.mean() if len(profits) > 0 else 0
        avg_loss = losses.mean() if len(losses) > 0 else 0

        # 盈亏比
        total_profit = profits.sum() if len(profits) > 0 else 0
        total_loss = abs(losses.sum()) if len(losses) > 0 else 1
        profit_factor = total_profit / total_loss if total_loss != 0 else 0

        # 期望值
        expectancy = closed_trades['profit_loss'].mean()

        return {
            'max_drawdown': round(max_drawdown, 2),
            'avg_profit': round(avg_profit, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(profit_factor, 2),
            'expectancy': round(expectancy, 2)
        }

    def get_direction_stats(self) -> Dict[str, Any]:
        """获取多空方向统计"""
        if self.trades.empty:
            return {
                'long': {'count': 0, 'profit_loss': 0, 'win_rate': 0, 'avg_profit': 0},
                'short': {'count': 0, 'profit_loss': 0, 'win_rate': 0, 'avg_profit': 0}
            }

        result = {}
        for direction in ['long', 'short']:
            direction_trades = self.trades[self.trades['direction'] == direction]
            closed = direction_trades[direction_trades['status'] == 'closed']

            if len(closed) > 0:
                result[direction] = {
                    'count': len(closed),
                    'profit_loss': round(closed['profit_loss'].sum(), 2),
                    'win_rate': round((closed['profit_loss'] > 0).sum() / len(closed) * 100, 2),
                    'avg_profit': round(closed['profit_loss'].mean(), 2)
                }
            else:
                result[direction] = {
                    'count': 0,
                    'profit_loss': 0,
                    'win_rate': 0,
                    'avg_profit': 0
                }

        return result


# 全局分析器实例
analyzer = TradeAnalyzer()
