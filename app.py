"""
Flask Web应用主入口
"""
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file, make_response
from loguru import logger
import sys
import os
from datetime import datetime

from config import SECRET_KEY, DEBUG, EXCHANGES, DIRECTIONS, STATUSES, TRENDS, SMM_MONTHLY_PRICE, LOG_LEVEL
from database import db
from models import Trade
from smm_model import SMMPrice
from futures_model import FuturesPrice
from product_model import Product
from physical_model import PhysicalPurchase, physical_db
from analyzers import analyzer
from utils import export_to_csv, import_from_csv, format_currency, format_percentage, get_color_for_value
from markupsafe import Markup


def get_sort_icon(column, current_order_by, current_order):
    """生成排序图标"""
    if current_order_by == column:
        if current_order == 'DESC':
            return Markup('<span class="ml-1 text-gray-600">↓</span>')
        else:
            return Markup('<span class="ml-1 text-gray-600">↑</span>')
    else:
        return Markup('<span class="ml-1 text-gray-300">↕</span>')


# 配置日志
logger.remove()
logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>", level=LOG_LEVEL)

# 完全关闭Werkzeug开发服务器的所有日志输出
import logging
logging.getLogger('werkzeug').setLevel(logging.CRITICAL)
logging.getLogger('werkzeug').disabled = True

# 创建Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['DEBUG'] = DEBUG

# 禁用Flask的访问日志
app.logger.setLevel(logging.CRITICAL)
log = logging.getLogger('werkzeug')
log.setLevel(logging.CRITICAL)
log.disabled = True


# ==================== 路由 ====================

@app.route('/')
def index():
    """首页仪表盘"""
    analyzer.reload()

    # 获取时间筛选参数
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # 获取SMM价格的月份参数（独立于时间筛选）
    month_param = request.args.get('month', '').strip()

    logger.info(f"仪表盘参数 - 时间筛选: {start_date} ~ {end_date}, SMM月份: {month_param}")

    # 获取所有交易数据（用于计算）
    all_trades = db.get_all_trades(order_by='trade_date', order='ASC')

    # 应用时间筛选
    filtered_trades = all_trades[:]
    if start_date:
        filtered_trades = [t for t in filtered_trades if t.trade_date >= start_date]
    if end_date:
        filtered_trades = [t for t in filtered_trades if t.trade_date <= end_date]

    # 计算筛选范围内的统计数据
    if filtered_trades:
        # 计算加权平均价格（基于筛选范围）
        total_entry_value = sum(t.entry_price * t.quantity for t in filtered_trades)
        total_entry_quantity = sum(t.quantity for t in filtered_trades)
        avg_entry_price = total_entry_value / total_entry_quantity if total_entry_quantity > 0 else 0

        # 计算结算价的加权平均
        settlement_trades = [t for t in filtered_trades if t.settlement_price]
        if settlement_trades:
            total_settlement_value = sum(t.settlement_price * t.quantity for t in settlement_trades)
            total_settlement_quantity = sum(t.quantity for t in settlement_trades)
            avg_settlement_price = total_settlement_value / total_settlement_quantity if total_settlement_quantity > 0 else 0
        else:
            avg_settlement_price = 0

        # 计算总交易数
        total_trades_count = len(filtered_trades)
        closed_trades_count = len([t for t in filtered_trades if t.status == 'closed'])
    else:
        avg_entry_price = 0
        avg_settlement_price = 0
        total_trades_count = 0
        closed_trades_count = 0

    # 计算SMM均价（基于月份选择，不受时间筛选影响）
    if month_param:
        # 根据月份计算（格式: 2024-01）
        year, month = month_param.split('-')
        smm_prices = db.get_smm_prices_by_month(int(year), int(month))
        if smm_prices:
            smm_price = sum(p.average_price for p in smm_prices) / len(smm_prices)
            smm_month_display = f"{year}年{month}月"
            smm_month = month_param  # 用于判断当前选中的月份
        else:
            # 月份内没有数据，使用最新价格
            latest_smm = db.get_latest_smm_price()
            smm_price = latest_smm.average_price if latest_smm else SMM_MONTHLY_PRICE
            smm_month_display = "最新（该月无数据）"
            smm_month = None
    else:
        # 默认使用最新的SMM价格
        latest_smm = db.get_latest_smm_price()
        if latest_smm:
            smm_price = latest_smm.average_price
            smm_month_display = "最新"
            smm_month = None
        else:
            smm_price = SMM_MONTHLY_PRICE
            smm_month_display = "默认"
            smm_month = None

    # 计算折扣（开仓价 vs SMM均价）
    if avg_entry_price and smm_price:
        entry_discount = ((smm_price - avg_entry_price) / smm_price) * 100
    else:
        entry_discount = 0

    # 计算折扣（结算价 vs SMM均价）
    if avg_settlement_price and smm_price:
        settlement_discount = ((smm_price - avg_settlement_price) / smm_price) * 100
    else:
        settlement_discount = 0

    logger.info(f"计算结果 - 平均开仓价: {avg_entry_price}, SMM价: {smm_price}, 开仓折扣: {entry_discount}%")
    logger.info(f"计算结果 - 平均结算价: {avg_settlement_price}, SMM价: {smm_price}, 结算折扣: {settlement_discount}%")

    # 按日期分组计算每天的开仓价、结算价和对应的SMM价格
    from collections import defaultdict
    daily_data = defaultdict(lambda: {'entry_price': 0, 'settlement_price': 0, 'entry_quantity': 0, 'settlement_quantity': 0, 'count': 0})
    for trade in filtered_trades:
        daily_data[trade.trade_date]['entry_price'] += trade.entry_price * trade.quantity
        daily_data[trade.trade_date]['entry_quantity'] += trade.quantity
        if trade.settlement_price:
            daily_data[trade.trade_date]['settlement_price'] += trade.settlement_price * trade.quantity
            daily_data[trade.trade_date]['settlement_quantity'] += trade.quantity
        daily_data[trade.trade_date]['count'] += 1

    # 准备图表数据
    chart_dates = []
    chart_entry_prices = []
    chart_settlement_prices = []
    chart_smm_prices = []
    chart_entry_discounts = []
    chart_settlement_discounts = []

    for date in sorted(daily_data.keys()):
        # 开仓价数据
        if daily_data[date]['entry_quantity'] > 0:
            avg_entry = daily_data[date]['entry_price'] / daily_data[date]['entry_quantity']
            chart_dates.append(date)
            chart_entry_prices.append(avg_entry)

            # 结算价数据（如果有）
            if daily_data[date]['settlement_quantity'] > 0:
                avg_settlement = daily_data[date]['settlement_price'] / daily_data[date]['settlement_quantity']
                chart_settlement_prices.append(avg_settlement)
            else:
                chart_settlement_prices.append(None)

            # 查找当天或最近之前的SMM价格
            daily_smm = db.get_smm_price_by_date(date)
            if daily_smm:
                smm = daily_smm.average_price
            else:
                smm = smm_price  # 使用当前选择的SMM均价

            chart_smm_prices.append(smm)

            # 计算每天的折扣（用于图表）
            daily_entry_discount = ((smm - avg_entry) / smm) * 100
            chart_entry_discounts.append(daily_entry_discount)

            if daily_data[date]['settlement_quantity'] > 0:
                daily_settlement_discount = ((smm - avg_settlement) / smm) * 100
                chart_settlement_discounts.append(daily_settlement_discount)
            else:
                chart_settlement_discounts.append(None)

    # 获取最近5条交易记录（不受筛选影响）
    recent_trades = db.get_all_trades(order_by='trade_date', order='DESC')[:5]

    # 获取全局统计数据（用于显示总览）
    global_stats = db.get_statistics()

    # 获取所有可用的月份列表（从SMM价格数据中提取）
    available_months = db.get_available_smm_months()

    response = make_response(render_template('index.html',
                          stats=global_stats,
                          recent_trades=recent_trades,
                          avg_entry_price=avg_entry_price,
                          avg_settlement_price=avg_settlement_price,
                          smm_price=smm_price,
                          entry_discount=entry_discount,
                          settlement_discount=settlement_discount,
                          smm_month=smm_month,
                          smm_month_display=smm_month_display,
                          total_trades_count=total_trades_count,
                          closed_trades_count=closed_trades_count,
                          available_months=available_months,
                          chart_dates=chart_dates,
                          chart_entry_prices=chart_entry_prices,
                          chart_settlement_prices=chart_settlement_prices,
                          chart_smm_prices=chart_smm_prices,
                          chart_entry_discounts=chart_entry_discounts,
                          chart_settlement_discounts=chart_settlement_discounts,
                          current_start_date=start_date,
                          current_end_date=end_date,
                          format_currency=format_currency,
                          format_percentage=format_percentage,
                          get_color_for_value=get_color_for_value))

    # 禁用缓存，确保数据实时更新
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    return response


@app.route('/trades')
def trades():
    """交易列表"""
    status_filter = request.args.get('status')
    product_filter = request.args.get('product')
    has_po_filter = request.args.get('has_po')  # 'yes' 或 'no'
    start_date = request.args.get('start_date')  # 开始日期
    end_date = request.args.get('end_date')  # 结束日期
    order_by = request.args.get('order_by', 'trade_date')
    order = request.args.get('order', 'DESC')
    month_param = request.args.get('month', '').strip()  # SMM月份参数

    all_trades = db.get_all_trades(
        status=status_filter,
        product=product_filter,
        order_by=order_by,
        order=order
    )

    # 应用关联PO筛选
    if has_po_filter == 'yes':
        all_trades = [t for t in all_trades if t.related_po and t.related_po.strip()]
    elif has_po_filter == 'no':
        all_trades = [t for t in all_trades if not t.related_po or not t.related_po.strip()]

    # 应用日期筛选
    if start_date:
        all_trades = [t for t in all_trades if t.trade_date >= start_date]
    if end_date:
        all_trades = [t for t in all_trades if t.trade_date <= end_date]

    # 获取筛选选项
    products = db.get_distinct_values('product_name')
    available_months = db.get_available_smm_months()

    # 计算筛选结果的加权平均价格
    if all_trades:
        # 计算加权平均开仓价
        total_entry_value = sum(t.entry_price * t.quantity for t in all_trades)
        total_entry_quantity = sum(t.quantity for t in all_trades)
        avg_entry_price = total_entry_value / total_entry_quantity if total_entry_quantity > 0 else 0

        # 计算加权平均结算价
        settlement_trades = [t for t in all_trades if t.settlement_price]
        if settlement_trades:
            total_settlement_value = sum(t.settlement_price * t.quantity for t in settlement_trades)
            total_settlement_quantity = sum(t.quantity for t in settlement_trades)
            avg_settlement_price = total_settlement_value / total_settlement_quantity if total_settlement_quantity > 0 else 0
        else:
            avg_settlement_price = 0
    else:
        avg_entry_price = 0
        avg_settlement_price = 0

    # 计算SMM均价（基于月份选择）
    if month_param:
        year, month = month_param.split('-')
        smm_prices = db.get_smm_prices_by_month(int(year), int(month))
        if smm_prices:
            smm_price = sum(p.average_price for p in smm_prices) / len(smm_prices)
            smm_month_display = f"{year}年{month}月"
            smm_month = month_param
        else:
            latest_smm = db.get_latest_smm_price()
            smm_price = latest_smm.average_price if latest_smm else SMM_MONTHLY_PRICE
            smm_month_display = "最新（该月无数据）"
            smm_month = None
    else:
        latest_smm = db.get_latest_smm_price()
        if latest_smm:
            smm_price = latest_smm.average_price
            smm_month_display = "最新"
            smm_month = None
        else:
            smm_price = SMM_MONTHLY_PRICE
            smm_month_display = "默认"
            smm_month = None

    # 计算折扣（开仓价 vs SMM均价）
    if avg_entry_price and smm_price:
        entry_discount = ((smm_price - avg_entry_price) / smm_price) * 100
    else:
        entry_discount = 0

    # 计算折扣（结算价 vs SMM均价）
    if avg_settlement_price and smm_price:
        settlement_discount = ((smm_price - avg_settlement_price) / smm_price) * 100
    else:
        settlement_discount = 0

    # 计算统计汇总
    totals = {
        'total_quantity': sum(t.quantity for t in all_trades),
        'total_physical_tons': sum(t.physical_tons or 0 for t in all_trades),
        'total_profit_loss': sum(t.profit_loss for t in all_trades if t.profit_loss),
        'total_fee': sum(t.fee for t in all_trades)
    }

    return render_template('trades.html',
                          trades=all_trades,
                          products=products,
                          current_status=status_filter,
                          current_product=product_filter,
                          current_has_po=has_po_filter,
                          current_start_date=start_date,
                          current_end_date=end_date,
                          current_order_by=order_by,
                          current_order=order,
                          totals=totals,
                          avg_entry_price=avg_entry_price,
                          avg_settlement_price=avg_settlement_price,
                          smm_price=smm_price,
                          smm_month=smm_month,
                          smm_month_display=smm_month_display,
                          entry_discount=entry_discount,
                          settlement_discount=settlement_discount,
                          available_months=available_months,
                          format_currency=format_currency,
                          get_color_for_value=get_color_for_value,
                          get_sort_icon=get_sort_icon)


@app.route('/trades/new', methods=['GET', 'POST'])
def new_trade():
    """新建交易"""
    if request.method == 'POST':
        try:
            # 获取数量和实物吨，如果用户输入了实物吨则使用，否则自动计算
            quantity = float(request.form['quantity'])
            physical_tons_input = request.form.get('physical_tons')
            if physical_tons_input and physical_tons_input.strip():
                physical_tons = float(physical_tons_input)
            else:
                # 自动计算并取整
                physical_tons = round(quantity * 1.13)

            trade = Trade(
                trade_date=request.form['trade_date'],
                exchange=request.form.get('exchange', 'gfex'),
                product_name=request.form.get('product_name', '碳酸锂'),
                contract=request.form.get('contract') or '',
                direction=request.form['direction'],
                entry_price=float(request.form['entry_price']),
                quantity=quantity,
                supplier=request.form.get('supplier') or None,
                settlement_price=float(request.form['settlement_price']) if request.form.get('settlement_price') else None,
                premium=float(request.form['premium']) if request.form.get('premium') else None,
                physical_tons=physical_tons,
                related_po=request.form.get('related_po') or None,
                stop_loss=None,  # 不再从表单接收
                take_profit=None,  # 不再从表单接收
                exit_price=float(request.form['exit_price']) if request.form.get('exit_price') else None,
                exit_date=request.form.get('exit_date') or None,
                fee=float(request.form.get('fee', 0) or 0),
                ma5=float(request.form['ma5']) if request.form.get('ma5') else None,
                ma10=float(request.form['ma10']) if request.form.get('ma10') else None,
                ma20=float(request.form['ma20']) if request.form.get('ma20') else None,
                rsi=float(request.form['rsi']) if request.form.get('rsi') else None,
                macd=float(request.form['macd']) if request.form.get('macd') else None,
                entry_reason=request.form.get('entry_reason') or None,
                market_trend=request.form.get('market_trend') or None,
                notes=request.form.get('notes') or None,
                status='closed' if request.form.get('exit_price') else 'open'
            )

            # 如果有平仓价格，计算盈亏
            if trade.exit_price:
                trade.calculate_profit_loss()

            db.create_trade(trade)
            flash('交易记录创建成功', 'success')
            return redirect(url_for('trades'))
        except Exception as e:
            logger.error(f"创建交易失败: {e}")
            import traceback
            traceback.print_exc()
            flash(f'创建交易失败: {str(e)}', 'error')

    # 获取所有品种（从交易记录中获取使用过的品种）
    product_list = db.get_distinct_values('product_name')

    return render_template('trade_form.html',
                          exchanges=EXCHANGES,
                          directions=DIRECTIONS,
                          trends=TRENDS,
                          products=product_list,
                          trade=None)


@app.route('/trades/<int:trade_id>/edit', methods=['GET', 'POST'])
def edit_trade(trade_id):
    """编辑交易"""
    trade = db.get_trade(trade_id)
    if not trade:
        flash('交易记录不存在', 'error')
        return redirect(url_for('trades'))

    if request.method == 'POST':
        try:
            trade.trade_date = request.form['trade_date']
            trade.exchange = request.form.get('exchange', trade.exchange)
            trade.product_name = request.form.get('product_name', trade.product_name)
            trade.contract = request.form.get('contract') or ''
            trade.direction = request.form['direction']
            trade.entry_price = float(request.form['entry_price'])
            trade.quantity = float(request.form['quantity'])

            # 处理实物吨
            physical_tons_input = request.form.get('physical_tons')
            if physical_tons_input and physical_tons_input.strip():
                trade.physical_tons = float(physical_tons_input)
            else:
                # 根据数量自动计算并取整
                trade.physical_tons = round(trade.quantity * 1.13)

            trade.supplier = request.form.get('supplier') or None
            trade.settlement_price = float(request.form['settlement_price']) if request.form.get('settlement_price') else None
            trade.premium = float(request.form['premium']) if request.form.get('premium') else None
            trade.related_po = request.form.get('related_po') or None
            trade.stop_loss = float(request.form['stop_loss']) if request.form.get('stop_loss') else None
            trade.take_profit = float(request.form['take_profit']) if request.form.get('take_profit') else None
            trade.exit_price = float(request.form['exit_price']) if request.form.get('exit_price') else None
            trade.exit_date = request.form.get('exit_date') or None
            trade.fee = float(request.form.get('fee', 0) or 0)
            trade.ma5 = float(request.form['ma5']) if request.form.get('ma5') else None
            trade.ma10 = float(request.form['ma10']) if request.form.get('ma10') else None
            trade.ma20 = float(request.form['ma20']) if request.form.get('ma20') else None
            trade.rsi = float(request.form['rsi']) if request.form.get('rsi') else None
            trade.macd = float(request.form['macd']) if request.form.get('macd') else None
            trade.entry_reason = request.form.get('entry_reason') or None
            trade.market_trend = request.form.get('market_trend') or None
            trade.notes = request.form.get('notes') or None
            trade.status = 'closed' if request.form.get('exit_price') else 'open'
            trade.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 如果有平仓价格，计算盈亏
            if trade.exit_price:
                trade.calculate_profit_loss()

            db.update_trade(trade)
            flash('交易记录更新成功', 'success')
            return redirect(url_for('trades'))
        except Exception as e:
            logger.error(f"更新交易失败: {e}")
            import traceback
            traceback.print_exc()
            flash(f'更新交易失败: {str(e)}', 'error')

    # 获取所有品种（从交易记录中获取使用过的品种）
    product_list = db.get_distinct_values('product_name')

    return render_template('trade_form.html',
                          exchanges=EXCHANGES,
                          directions=DIRECTIONS,
                          trends=TRENDS,
                          products=product_list,
                          trade=trade)


@app.route('/trades/<int:trade_id>/delete', methods=['POST'])
def delete_trade(trade_id):
    """删除交易"""
    if db.delete_trade(trade_id):
        flash('交易记录已删除', 'success')
    else:
        flash('删除失败', 'error')
    return redirect(url_for('trades'))


@app.route('/trades/<int:trade_id>/close', methods=['POST'])
def close_trade(trade_id):
    """平仓操作"""
    trade = db.get_trade(trade_id)
    if not trade:
        flash('交易记录不存在', 'error')
        return redirect(url_for('trades'))

    if trade.status == 'closed':
        flash('该交易已经平仓', 'warning')
        return redirect(url_for('trades'))

    exit_price = request.form.get('exit_price')
    exit_date = request.form.get('exit_date')

    if not exit_price or not exit_date:
        flash('请提供平仓价格和日期', 'error')
        return redirect(url_for('trades'))

    try:
        trade.exit_price = float(exit_price)
        trade.exit_date = exit_date
        trade.status = 'closed'
        trade.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        trade.calculate_profit_loss()
        db.update_trade(trade)
        flash(f'交易已平仓，盈亏: {format_currency(trade.profit_loss)}', 'success')
    except Exception as e:
        logger.error(f"平仓失败: {e}")
        flash(f'平仓失败: {str(e)}', 'error')

    return redirect(url_for('trades'))


@app.route('/statistics')
def statistics():
    """统计分析页面"""
    analyzer.reload()

    # 获取基础统计
    stats = db.get_statistics()

    # 获取分析数据
    monthly_stats = analyzer.get_monthly_stats()
    product_performance = analyzer.get_product_performance()
    win_rate_trend = analyzer.get_win_rate_trend()
    price_trend = analyzer.get_price_trend()
    risk_metrics = analyzer.get_risk_metrics()
    direction_stats = analyzer.get_direction_stats()

    return render_template('statistics.html',
                          stats=stats,
                          monthly_stats=monthly_stats,
                          product_performance=product_performance,
                          win_rate_trend=win_rate_trend,
                          price_trend=price_trend,
                          risk_metrics=risk_metrics,
                          direction_stats=direction_stats,
                          format_currency=format_currency,
                          format_percentage=format_percentage,
                          get_color_for_value=get_color_for_value)


# ==================== API 路由 ====================

@app.route('/api/trades')
def api_trades():
    """API: 获取交易数据"""
    trades = db.get_all_trades()
    return jsonify([trade.to_dict() for trade in trades])


@app.route('/api/statistics')
def api_statistics():
    """API: 获取统计数据"""
    analyzer.reload()
    stats = db.get_statistics()

    return jsonify({
        'basic': stats,
        'monthly': analyzer.get_monthly_stats(),
        'products': analyzer.get_product_performance(),
        'win_rate_trend': analyzer.get_win_rate_trend(),
        'risk_metrics': analyzer.get_risk_metrics(),
        'direction_stats': analyzer.get_direction_stats()
    })


@app.route('/export/csv')
def export_csv():
    """导出CSV"""
    filepath = export_to_csv()
    return send_file(filepath, as_attachment=True)


@app.route('/import', methods=['POST'])
def import_data():
    """导入数据"""
    if 'file' not in request.files:
        flash('没有上传文件', 'error')
        return redirect(url_for('trades'))

    file = request.files['file']
    if file.filename == '':
        flash('没有选择文件', 'error')
        return redirect(url_for('trades'))

    if file and file.filename.endswith('.csv'):
        try:
            # 保存临时文件
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as tmp:
                tmp.write(file.read().decode('utf-8'))
                tmp_path = tmp.name

            count = import_from_csv(tmp_path)
            flash(f'成功导入 {count} 条交易记录', 'success')

            # 删除临时文件
            import os
            os.unlink(tmp_path)
        except Exception as e:
            logger.error(f"导入失败: {e}")
            flash(f'导入失败: {str(e)}', 'error')
    else:
        flash('请上传CSV文件', 'error')

    return redirect(url_for('trades'))


# ==================== SMM价格管理 ====================

@app.route('/smm_prices')
def smm_prices():
    """SMM价格管理页面"""
    prices = db.get_all_smm_prices()
    return render_template('smm_prices.html', prices=prices)


@app.route('/smm_prices/new', methods=['GET', 'POST'])
def new_smm_price():
    """新建SMM价格记录"""
    if request.method == 'POST':
        try:
            smm_price = SMMPrice(
                price_date=request.form['price_date'],
                highest_price=float(request.form['highest_price']),
                lowest_price=float(request.form['lowest_price']),
                average_price=float(request.form['average_price'])
            )
            db.create_smm_price(smm_price)
            flash('SMM价格记录创建成功', 'success')
            return redirect(url_for('smm_prices'))
        except Exception as e:
            logger.error(f"创建SMM价格失败: {e}")
            flash(f'创建失败: {str(e)}', 'error')

    return render_template('smm_price_form.html', smm_price=None)


@app.route('/smm_prices/<int:price_id>/edit', methods=['GET', 'POST'])
def edit_smm_price(price_id):
    """编辑SMM价格记录"""
    smm_price = db.get_smm_price(price_id)
    if not smm_price:
        flash('SMM价格记录不存在', 'error')
        return redirect(url_for('smm_prices'))

    if request.method == 'POST':
        try:
            smm_price.price_date = request.form['price_date']
            smm_price.highest_price = float(request.form['highest_price'])
            smm_price.lowest_price = float(request.form['lowest_price'])
            smm_price.average_price = float(request.form['average_price'])
            smm_price.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            db.update_smm_price(smm_price)
            flash('SMM价格记录更新成功', 'success')
            return redirect(url_for('smm_prices'))
        except Exception as e:
            logger.error(f"更新SMM价格失败: {e}")
            flash(f'更新失败: {str(e)}', 'error')

    return render_template('smm_price_form.html', smm_price=smm_price)


@app.route('/smm_prices/<int:price_id>/delete', methods=['POST'])
def delete_smm_price(price_id):
    """删除SMM价格记录"""
    if db.delete_smm_price(price_id):
        flash('SMM价格记录已删除', 'success')
    else:
        flash('删除失败', 'error')
    return redirect(url_for('smm_prices'))


@app.route('/smm_prices/import', methods=['POST'])
def import_smm_prices():
    """通过Excel导入SMM价格数据"""
    if 'file' not in request.files:
        flash('没有上传文件', 'error')
        return redirect(url_for('smm_prices'))

    file = request.files['file']
    if file.filename == '':
        flash('没有选择文件', 'error')
        return redirect(url_for('smm_prices'))

    if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        flash('请上传Excel文件（.xlsx 或 .xls）', 'error')
        return redirect(url_for('smm_prices'))

    try:
        import pandas as pd
        import tempfile
        import os

        # 保存临时文件
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.xlsx', delete=False) as tmp:
            tmp.write(file.read())
            tmp_path = tmp.name

        try:
            # 读取Excel文件
            df = pd.read_excel(tmp_path)

            # 检查必需的列
            required_columns = ['日期', '最高价', '最低价', '均价']
            missing_columns = [col for col in required_columns if col not in df.columns]

            if missing_columns:
                flash(f'Excel文件缺少必需的列: {", ".join(missing_columns)}', 'error')
                return redirect(url_for('smm_prices'))

            # 批量插入数据
            success_count = 0
            for _, row in df.iterrows():
                try:
                    smm_price = SMMPrice(
                        price_date=str(row['日期'])[:10],  # 确保日期格式正确
                        highest_price=float(row['最高价']),
                        lowest_price=float(row['最低价']),
                        average_price=float(row['均价'])
                    )
                    db.create_smm_price(smm_price)
                    success_count += 1
                except Exception as e:
                    logger.error(f"插入行数据失败: {e}")
                    continue

            flash(f'成功导入 {success_count} 条价格记录', 'success')

        finally:
            # 删除临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except Exception as e:
        logger.error(f"导入失败: {e}")
        import traceback
        traceback.print_exc()
        flash(f'导入失败: {str(e)}', 'error')

    return redirect(url_for('smm_prices'))


@app.route('/smm_prices/template')
def download_smm_template():
    """下载SMM价格导入模板"""
    import pandas as pd
    from io import BytesIO

    # 创建模板数据
    template_data = {
        '日期': ['2024-01-31', '2024-02-29', ''],
        '最高价': [127000, 128000, ''],
        '最低价': [123000, 124000, ''],
        '均价': [125000, 126000, '']
    }

    df = pd.DataFrame(template_data)

    # 输出到Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='SMM价格')

    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name='smm_price_template.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@app.route('/update_smm_price', methods=['POST'])
def update_smm_price():
    """更新SMM月均价（保留用于快速更新）"""
    try:
        new_price = float(request.form['smm_price'])
        # 更新config.py文件中的SMM_MONTHLY_PRICE
        config_path = os.path.join(os.path.dirname(__file__), 'config.py')

        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 替换SMM_MONTHLY_PRICE的值
        import re
        content = re.sub(
            r'SMM_MONTHLY_PRICE\s*=\s*[\d.]+',
            f'SMM_MONTHLY_PRICE = {new_price}',
            content
        )

        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(content)

        flash(f'SMM月均价已更新为 {new_price} 元/吨', 'success')
    except Exception as e:
        logger.error(f"更新SMM价格失败: {e}")
        flash(f'更新失败: {str(e)}', 'error')

    return redirect(url_for('index'))


# ==================== 期货价格管理 ====================

@app.route('/futures_prices')
def futures_prices():
    """期货价格管理页面"""
    prices = db.get_all_futures_prices()
    return render_template('futures_prices.html', prices=prices)


@app.route('/futures_prices/new', methods=['GET', 'POST'])
def new_futures_price():
    """新建期货价格记录"""
    if request.method == 'POST':
        try:
            futures_price = FuturesPrice(
                price_date=request.form['price_date'],
                highest_price=float(request.form['highest_price']),
                lowest_price=float(request.form['lowest_price']),
                average_price=float(request.form['average_price'])
            )
            db.create_futures_price(futures_price)
            flash('期货价格记录创建成功', 'success')
            return redirect(url_for('futures_prices'))
        except Exception as e:
            logger.error(f"创建期货价格失败: {e}")
            flash(f'创建失败: {str(e)}', 'error')

    return render_template('futures_price_form.html', price=None)


@app.route('/futures_prices/<int:price_id>/edit', methods=['GET', 'POST'])
def edit_futures_price(price_id):
    """编辑期货价格记录"""
    futures_price = db.get_futures_price(price_id)
    if not futures_price:
        flash('期货价格记录不存在', 'error')
        return redirect(url_for('futures_prices'))

    if request.method == 'POST':
        try:
            futures_price.price_date = request.form['price_date']
            futures_price.highest_price = float(request.form['highest_price'])
            futures_price.lowest_price = float(request.form['lowest_price'])
            futures_price.average_price = float(request.form['average_price'])
            futures_price.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            db.update_futures_price(futures_price)
            flash('期货价格记录更新成功', 'success')
            return redirect(url_for('futures_prices'))
        except Exception as e:
            logger.error(f"更新期货价格失败: {e}")
            flash(f'更新失败: {str(e)}', 'error')

    return render_template('futures_price_form.html', price=futures_price)


@app.route('/futures_prices/<int:price_id>/delete', methods=['POST'])
def delete_futures_price(price_id):
    """删除期货价格记录"""
    if db.delete_futures_price(price_id):
        flash('期货价格记录已删除', 'success')
    else:
        flash('删除失败', 'error')
    return redirect(url_for('futures_prices'))


@app.route('/futures_prices/import', methods=['POST'])
def import_futures_prices():
    """通过Excel导入期货价格数据"""
    if 'file' not in request.files:
        flash('没有上传文件', 'error')
        return redirect(url_for('futures_prices'))

    file = request.files['file']
    if file.filename == '':
        flash('没有选择文件', 'error')
        return redirect(url_for('futures_prices'))

    if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        flash('请上传Excel文件（.xlsx 或 .xls）', 'error')
        return redirect(url_for('futures_prices'))

    try:
        import pandas as pd
        import tempfile
        import os

        # 保存临时文件
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.xlsx', delete=False) as tmp:
            tmp.write(file.read())
            tmp_path = tmp.name

        try:
            # 读取Excel文件
            df = pd.read_excel(tmp_path)

            # 检查必需的列
            required_columns = ['日期', '最高价', '最低价', '均价']
            missing_columns = [col for col in required_columns if col not in df.columns]

            if missing_columns:
                flash(f'Excel文件缺少必需的列: {", ".join(missing_columns)}', 'error')
                return redirect(url_for('futures_prices'))

            # 批量插入数据
            success_count = 0
            for _, row in df.iterrows():
                try:
                    futures_price = FuturesPrice(
                        price_date=str(row['日期'])[:10],
                        highest_price=float(row['最高价']),
                        lowest_price=float(row['最低价']),
                        average_price=float(row['均价'])
                    )
                    db.create_futures_price(futures_price)
                    success_count += 1
                except Exception as e:
                    logger.error(f"插入行数据失败: {e}")
                    continue

            flash(f'成功导入 {success_count} 条价格记录', 'success')

        finally:
            # 删除临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except Exception as e:
        logger.error(f"导入失败: {e}")
        import traceback
        traceback.print_exc()
        flash(f'导入失败: {str(e)}', 'error')

    return redirect(url_for('futures_prices'))


@app.route('/futures_prices/template')
def download_futures_template():
    """下载期货价格导入模板"""
    import pandas as pd
    from io import BytesIO

    # 创建模板数据
    template_data = {
        '日期': ['2024-01-31', '2024-02-29', ''],
        '最高价': [127000, 128000, ''],
        '最低价': [123000, 124000, ''],
        '均价': [125000, 126000, '']
    }

    df = pd.DataFrame(template_data)

    # 输出到Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='期货价格')

    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name='futures_price_template.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


# ==================== 实物采购管理 ====================

@app.route('/physical_purchases')
def physical_purchases():
    """实物采购列表"""
    status_filter = request.args.get('status')
    supplier_filter = request.args.get('supplier')
    product_filter = request.args.get('product')

    all_purchases = physical_db.get_all_purchases(
        status=status_filter,
        supplier=supplier_filter,
        product=product_filter,
        order_by='purchase_date',
        order='DESC'
    )

    # 获取所有期货交易（用于关联选择）
    all_trades = db.get_all_trades(order_by='trade_date', order='DESC')

    # 获取筛选选项
    suppliers = physical_db.get_distinct_suppliers()
    products = physical_db.get_distinct_products()

    # 计算统计汇总
    totals = {
        'total_quantity': sum(p.quantity for p in all_purchases),
        'total_amount': sum(p.total_amount for p in all_purchases),
        'total_count': len(all_purchases)
    }

    return render_template('physical_purchases.html',
                          purchases=all_purchases,
                          trades=all_trades,
                          suppliers=suppliers,
                          products=products,
                          current_status=status_filter,
                          current_supplier=supplier_filter,
                          current_product=product_filter,
                          totals=totals,
                          physical_db=physical_db,
                          format_currency=format_currency)


@app.route('/physical_purchases/new', methods=['GET', 'POST'])
def new_physical_purchase():
    """新建实物记录"""
    if request.method == 'POST':
        try:
            # 计算总金额
            quantity = float(request.form['quantity'])
            unit_price_str = request.form.get('unit_price')
            premium_str = request.form.get('premium', '')

            # 处理贴水 - 空字符串转为0
            premium = float(premium_str) if premium_str and premium_str.strip() else 0.0

            # 如果没有单价，使用期货保值价格
            if unit_price_str and unit_price_str.strip():
                unit_price = float(unit_price_str)
            else:
                unit_price = 0  # 根据关联的期货价格计算

            total_amount = quantity * (unit_price + premium) if unit_price else quantity * premium

            # 获取关联的期货交易ID列表
            related_trade_ids = request.form.getlist('related_trade_ids')

            purchase = PhysicalPurchase(
                purchase_date=request.form['purchase_date'],
                supplier=request.form.get('supplier') or None,
                product_name=request.form.get('product_name', '碳酸锂'),
                quantity=quantity,
                unit_price=unit_price if unit_price else None,
                premium=premium,
                total_amount=total_amount,
                po_number=request.form.get('po_number') or None,
                delivery_date=request.form.get('delivery_date') or None,
                status=request.form.get('status', 'pending'),
                notes=request.form.get('notes') or None
            )

            physical_db.create_purchase(purchase, related_trade_ids)
            flash('实物记录创建成功！', 'success')
            return redirect(url_for('physical_purchases'))

        except Exception as e:
            flash(f'创建失败: {str(e)}', 'error')
            logger.error(f"创建实物记录失败: {e}")
            return redirect(url_for('physical_purchases'))

    # GET请求 - 显示新建表单
    all_trades = db.get_all_trades(order_by='trade_date', order='DESC')
    return render_template('physical_purchase_form.html',
                          trades=all_trades,
                          action='new')


@app.route('/physical_purchases/<int:purchase_id>/edit', methods=['GET', 'POST'])
def edit_physical_purchase(purchase_id):
    """编辑实物记录"""
    purchase = physical_db.get_purchase_by_id(purchase_id)

    if not purchase:
        flash('实物记录不存在', 'error')
        return redirect(url_for('physical_purchases'))

    if request.method == 'POST':
        try:
            # 计算总金额
            quantity = float(request.form['quantity'])
            unit_price_str = request.form.get('unit_price')
            premium_str = request.form.get('premium', '')

            # 处理贴水 - 空字符串转为0
            premium = float(premium_str) if premium_str and premium_str.strip() else 0.0

            # 如果没有单价，使用期货保值价格
            if unit_price_str and unit_price_str.strip():
                unit_price = float(unit_price_str)
            else:
                unit_price = 0

            total_amount = quantity * (unit_price + premium) if unit_price else quantity * premium

            # 获取关联的期货交易ID列表
            related_trade_ids = request.form.getlist('related_trade_ids')

            purchase.purchase_date = request.form['purchase_date']
            purchase.supplier = request.form.get('supplier') or None
            purchase.product_name = request.form.get('product_name', '碳酸锂')
            purchase.quantity = quantity
            purchase.unit_price = unit_price if unit_price else None
            purchase.premium = premium
            purchase.total_amount = total_amount
            purchase.po_number = request.form.get('po_number') or None
            purchase.delivery_date = request.form.get('delivery_date') or None
            purchase.status = request.form.get('status', 'pending')
            purchase.notes = request.form.get('notes') or None

            physical_db.update_purchase(purchase, related_trade_ids)
            flash('实物记录更新成功！', 'success')
            return redirect(url_for('physical_purchases'))

        except Exception as e:
            flash(f'更新失败: {str(e)}', 'error')
            logger.error(f"更新实物记录失败: {e}")
            return redirect(url_for('physical_purchases'))

    # GET请求 - 显示编辑表单
    all_trades = db.get_all_trades(order_by='trade_date', order='DESC')
    # 获取当前采购记录关联的期货交易
    related_trades = physical_db.get_related_trades(purchase_id)
    related_trade_ids = [t.id for t in related_trades]

    return render_template('physical_purchase_form.html',
                          purchase=purchase,
                          trades=all_trades,
                          related_trade_ids=related_trade_ids,
                          action='edit')


@app.route('/physical_purchases/<int:purchase_id>/delete', methods=['POST'])
def delete_physical_purchase(purchase_id):
    """删除实物记录"""
    try:
        physical_db.delete_purchase(purchase_id)
        flash('实物记录已删除', 'success')
    except Exception as e:
        flash(f'删除失败: {str(e)}', 'error')
        logger.error(f"删除实物记录失败: {e}")

    return redirect(url_for('physical_purchases'))


@app.route('/api/purchases/<int:purchase_id>/trades')
def api_purchase_trades(purchase_id):
    """获取采购记录关联的所有期货交易（API）"""
    try:
        trades = physical_db.get_related_trades(purchase_id)
        return jsonify({
            'success': True,
            'trades': [t.to_dict() for t in trades]
        })
    except Exception as e:
        logger.error(f"获取关联期货交易失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/purchases/<int:purchase_id>/trades', methods=['POST'])
def api_update_purchase_trades(purchase_id):
    """更新采购记录的关联期货交易（API）"""
    try:
        data = request.get_json()
        trade_ids = data.get('trade_ids', [])

        # 先删除旧的关联关系
        with physical_db.get_connection() as conn:
            conn.execute('DELETE FROM purchase_trade_relations WHERE purchase_id = ?', (purchase_id,))

            # 添加新的关联关系
            for trade_id in trade_ids:
                if trade_id:  # 跳过空值
                    conn.execute('''
                        INSERT INTO purchase_trade_relations (purchase_id, trade_id, created_at)
                        VALUES (?, ?, ?)
                    ''', (purchase_id, trade_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()

        return jsonify({
            'success': True,
            'message': '关联更新成功'
        })
    except Exception as e:
        logger.error(f"更新关联期货交易失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/trades/<int:trade_id>/purchases')
def api_trade_purchases(trade_id):
    """获取期货交易关联的所有采购记录（API）"""
    try:
        purchases = physical_db.get_related_purchases(trade_id)
        return jsonify({
            'success': True,
            'purchases': [p.to_dict() for p in purchases]
        })
    except Exception as e:
        logger.error(f"获取关联采购记录失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/trades/<int:trade_id>/purchases/add', methods=['POST'])
def api_add_trade_purchase(trade_id):
    """为期货交易关联采购订单（API）"""
    try:
        data = request.get_json()
        purchase_id = data.get('purchase_id')

        if not purchase_id:
            return jsonify({
                'success': False,
                'error': '缺少采购订单ID'
            }), 400

        success = physical_db.add_trade_relation(purchase_id, trade_id)

        if success:
            return jsonify({
                'success': True,
                'message': '关联成功'
            })
        else:
            return jsonify({
                'success': False,
                'error': '关联已存在或创建失败'
            }), 400
    except Exception as e:
        logger.error(f"关联采购订单失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/trades/<int:trade_id>/purchases/remove', methods=['POST'])
def api_remove_trade_purchase(trade_id):
    """取消期货交易与采购订单的关联（API）"""
    try:
        data = request.get_json()
        purchase_id = data.get('purchase_id')

        if not purchase_id:
            return jsonify({
                'success': False,
                'error': '缺少采购订单ID'
            }), 400

        physical_db.remove_trade_relation(purchase_id, trade_id)

        return jsonify({
            'success': True,
            'message': '取消关联成功'
        })
    except Exception as e:
        logger.error(f"取消关联采购订单失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/purchases/list')
def api_purchases_list():
    """获取所有采购订单列表（用于关联选择）"""
    try:
        status = request.args.get('status')
        product = request.args.get('product')

        purchases = physical_db.get_all_purchases(status=status, product=product)

        return jsonify({
            'success': True,
            'purchases': [p.to_dict() for p in purchases]
        })
    except Exception as e:
        logger.error(f"获取采购订单列表失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    logger.info("启动期货交易记录系统...")
    logger.info("访问地址: http://localhost:5001")

    # 禁用Werkzeug的访问日志
    import io
    import sys

    class Filtered_stderr:
        """过滤掉Werkzeug访问日志的stderr"""
        def __init__(self, original_stderr):
            self.original_stderr = original_stderr

        def write(self, text):
            # 过滤掉访问日志行
            if text.strip() and not (
                '"GET /' in text or
                '"POST /' in text or
                '"PUT /' in text or
                '"DELETE /' in text or
                'HTTP/1.1' in text and ('200' in text or '302' in text or '404' in text or '500' in text)
            ):
                self.original_stderr.write(text)

        def flush(self):
            self.original_stderr.flush()

    # 应用过滤器
    if not DEBUG:
        sys.stderr = Filtered_stderr(sys.stderr)

    app.run(host='0.0.0.0', port=5001, debug=DEBUG)
