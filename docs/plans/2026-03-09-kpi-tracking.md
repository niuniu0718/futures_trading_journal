# A+F KPI追踪功能实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标：** 新增KPI追踪页面，用于追踪碳酸锂和氢氧化锂的采购情况，与SMM均价对比计算降本

**架构：** 遵循现有项目架构，创建新的KPI模块（kpi_model.py），在app.py中添加路由，创建kpi.html模板页面

**技术栈：** Flask + SQLite + Jinja2 + Tailwind CSS + Alpine.js

---

## Task 1: 创建KPI数据模型

**Files:**
- Create: `kpi_model.py`

**Step 1: 创建KPI模型文件**

```python
"""
KPI追踪模型 - Actual + Forecast
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class KPIRecord:
    """KPI记录数据模型"""
    id: Optional[int] = None
    month: str = None  # 月份 YYYY-MM
    product_name: str = None  # 品种：碳酸锂/氢氧化锂
    actual_quantity: Optional[float] = None  # 实际采购量（吨）
    actual_avg_price: Optional[float] = None  # 实际均价
    forecast_quantity: Optional[float] = None  # 预测采购量（吨）
    forecast_avg_price: Optional[float] = None  # 预测均价
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        """初始化后处理"""
        if self.created_at is None:
            self.created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if self.updated_at is None:
            self.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'month': self.month,
            'product_name': self.product_name,
            'actual_quantity': self.actual_quantity,
            'actual_avg_price': self.actual_avg_price,
            'forecast_quantity': self.forecast_quantity,
            'forecast_avg_price': self.forecast_avg_price,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


class KPIDB:
    """KPI数据库管理类"""

    def __init__(self, db_path='data/trading_journal.db'):
        self.db_path = db_path
        self.init_table()

    def get_connection(self):
        """获取数据库连接"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_table(self):
        """初始化KPI表"""
        with self.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS kpi_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    month TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    actual_quantity REAL,
                    actual_avg_price REAL,
                    forecast_quantity REAL,
                    forecast_avg_price REAL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(month, product_name)
                )
            ''')
            conn.commit()

    def create_record(self, record):
        """创建新记录"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO kpi_records
                (month, product_name, actual_quantity, actual_avg_price,
                 forecast_quantity, forecast_avg_price, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (record.month, record.product_name, record.actual_quantity,
                  record.actual_avg_price, record.forecast_quantity,
                  record.forecast_avg_price, record.created_at, record.updated_at))
            conn.commit()
            record.id = cursor.lastrowid
            return record

    def get_record_by_id(self, record_id):
        """根据ID获取记录"""
        with self.get_connection() as conn:
            row = conn.execute('SELECT * FROM kpi_records WHERE id = ?', (record_id,)).fetchone()
            if row:
                return KPIRecord(
                    id=row['id'], month=row['month'], product_name=row['product_name'],
                    actual_quantity=row['actual_quantity'], actual_avg_price=row['actual_avg_price'],
                    forecast_quantity=row['forecast_quantity'], forecast_avg_price=row['forecast_avg_price'],
                    created_at=row['created_at'], updated_at=row['updated_at']
                )
            return None

    def get_all_records(self, product=None, order_by='month', order='DESC'):
        """获取所有记录"""
        with self.get_connection() as conn:
            query = 'SELECT * FROM kpi_records WHERE 1=1'
            params = []

            if product:
                query += ' AND product_name = ?'
                params.append(product)

            query += f' ORDER BY {order_by} {order}'
            rows = conn.execute(query, params).fetchall()

            records = []
            for row in rows:
                records.append(KPIRecord(
                    id=row['id'], month=row['month'], product_name=row['product_name'],
                    actual_quantity=row['actual_quantity'], actual_avg_price=row['actual_avg_price'],
                    forecast_quantity=row['forecast_quantity'], forecast_avg_price=row['forecast_avg_price'],
                    created_at=row['created_at'], updated_at=row['updated_at']
                ))
            return records

    def update_record(self, record):
        """更新记录"""
        record.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with self.get_connection() as conn:
            conn.execute('''
                UPDATE kpi_records
                SET month=?, product_name=?, actual_quantity=?, actual_avg_price=?,
                    forecast_quantity=?, forecast_avg_price=?, updated_at=?
                WHERE id=?
            ''', (record.month, record.product_name, record.actual_quantity,
                  record.actual_avg_price, record.forecast_quantity,
                  record.forecast_avg_price, record.updated_at, record.id))
            conn.commit()
            return record

    def delete_record(self, record_id):
        """删除记录"""
        with self.get_connection() as conn:
            conn.execute('DELETE FROM kpi_records WHERE id = ?', (record_id,))
            conn.commit()

    def get_monthly_stats(self, month=None):
        """获取月度统计数据"""
        with self.get_connection() as conn:
            if month:
                query = '''
                    SELECT product_name,
                           SUM(actual_quantity) as total_actual_qty,
                           AVG(actual_avg_price) as avg_actual_price,
                           SUM(forecast_quantity) as total_forecast_qty,
                           AVG(forecast_avg_price) as avg_forecast_price
                    FROM kpi_records
                    WHERE month = ? AND actual_quantity IS NOT NULL
                    GROUP BY product_name
                '''
                rows = conn.execute(query, (month,)).fetchall()
            else:
                # 获取最新月份的统计
                query = '''
                    SELECT product_name,
                           SUM(actual_quantity) as total_actual_qty,
                           AVG(actual_avg_price) as avg_actual_price,
                           SUM(forecast_quantity) as total_forecast_qty,
                           AVG(forecast_avg_price) as avg_forecast_price
                    FROM kpi_records
                    WHERE month = (SELECT MAX(month) FROM kpi_records) AND actual_quantity IS NOT NULL
                    GROUP BY product_name
                '''
                rows = conn.execute(query).fetchall()

            stats = {}
            for row in rows:
                stats[row['product_name']] = {
                    'total_actual_qty': row['total_actual_qty'] or 0,
                    'avg_actual_price': row['avg_actual_price'] or 0,
                    'total_forecast_qty': row['total_forecast_qty'] or 0,
                    'avg_forecast_price': row['avg_forecast_price'] or 0
                }
            return stats


# 创建全局实例
kpi_db = KPIDB()
```

**Step 2: 验证文件创建成功**

Run: `ls -la /Users/niuniu/cc/futures_trading_journal/kpi_model.py`
Expected: 文件存在

**Step 3: 测试模型导入**

```python
# 在Python交互环境中测试
from kpi_model import KPIRecord, kpi_db

# 测试创建表（应该自动创建）
print("KPI模型导入成功")
```

Run: `python3 -c "from kpi_model import KPIRecord, kpi_db; print('KPI模型导入成功')"`
Expected: 输出 "KPI模型导入成功"

**Step 4: 提交**

```bash
git add kpi_model.py
git commit -m "feat: 添加KPI追踪数据模型"
```

---

## Task 2: 在database.py中添加SMM按月查询方法

**Files:**
- Modify: `database.py`

**Step 1: 添加get_smm_prices_by_month方法**

在 `database.py` 的 `DatabaseManager` 类中，确认存在或添加 `get_smm_prices_by_month` 方法。检查文件头部是否已有此方法的导入。

查看文件，确认以下方法存在（约在app.py中的calculate_smm_price函数也使用了类似逻辑）：

```python
def get_smm_prices_by_month(self, year, month):
    """获取指定月份的所有SMM价格记录"""
    with self.get_connection() as conn:
        month_pattern = f"{year}-{month:02d}"
        rows = conn.execute(
            'SELECT * FROM smm_prices WHERE price_date LIKE ? ORDER BY price_date',
            (f"{month_pattern}%",)
        ).fetchall()

        prices = []
        for row in rows:
            prices.append(SMMPrice(
                id=row['id'], price_date=row['price_date'],
                highest_price=row['highest_price'], lowest_price=row['lowest_price'],
                average_price=row['average_price'], created_at=row['created_at'],
                updated_at=row['updated_at']
            ))
        return prices
```

Run: `grep -n "get_smm_prices_by_month" /Users/niuniu/cc/futures_trading_journal/database.py`
Expected: 找到方法定义

**Step 2: 如果方法不存在，添加到database.py**

找到 `DatabaseManager` 类中合适的位置（在其他查询方法附近）添加上述方法。

**Step 3: 提交**

```bash
git add database.py
git commit -m "feat: 确保database.py中有get_smm_prices_by_month方法"
```

---

## Task 3: 在app.py中添加KPI路由

**Files:**
- Modify: `app.py`

**Step 1: 导入KPI模块**

在文件顶部的import区域添加：

```python
from kpi_model import KPIRecord, kpi_db
```

找到类似 `from physical_model import PhysicalPurchase, physical_db` 的位置，在其后添加。

**Step 2: 添加KPI列表页路由**

在app.py的路由区域（约100行之后）添加：

```python
@app.route('/kpi')
def kpi():
    """KPI追踪主页"""
    from datetime import datetime

    # 获取筛选参数
    product_filter = request.args.get('product', '')

    # 获取所有记录
    records = kpi_db.get_all_records(product=product_filter if product_filter else None)

    # 获取统计数据
    current_month = datetime.now().strftime('%Y-%m')
    stats = kpi_db.get_monthly_stats(month=current_month)

    # 计算降本数据
    for record in records:
        # 获取该月SMM均价
        year, month = record.month.split('-')
        smm_prices = db.get_smm_prices_by_month(int(year), int(month))
        if smm_prices:
            smm_avg = sum(p.average_price for p in smm_prices) / len(smm_prices)
            record.smm_avg_price = smm_avg
            # 计算降本
            if record.actual_avg_price:
                record.cost_saving = smm_avg - record.actual_avg_price
                record.cost_saving_pct = (record.cost_saving / smm_avg * 100) if smm_avg > 0 else 0
            else:
                record.cost_saving = None
                record.cost_saving_pct = None
        else:
            record.smm_avg_price = None
            record.cost_saving = None
            record.cost_saving_pct = None

    # 获取品种列表
    products = ['碳酸锂', '氢氧化锂']

    return render_template('kpi.html',
                          records=records,
                          stats=stats,
                          products=products,
                          current_product=product_filter,
                          current_month=current_month)
```

**Step 3: 添加创建KPI记录路由**

```python
@app.route('/kpi/new', methods=['POST'])
def new_kpi_record():
    """创建新的KPI记录"""
    try:
        record = KPIRecord(
            month=request.form.get('month'),
            product_name=request.form.get('product_name'),
            actual_quantity=float(request.form.get('actual_quantity')) if request.form.get('actual_quantity') else None,
            actual_avg_price=float(request.form.get('actual_avg_price')) if request.form.get('actual_avg_price') else None,
            forecast_quantity=float(request.form.get('forecast_quantity')) if request.form.get('forecast_quantity') else None,
            forecast_avg_price=float(request.form.get('forecast_avg_price')) if request.form.get('forecast_avg_price') else None
        )
        kpi_db.create_record(record)
        flash('KPI记录创建成功', 'success')
    except Exception as e:
        flash(f'创建失败: {str(e)}', 'error')

    return redirect(url_for('kpi'))
```

**Step 4: 添加编辑KPI记录路由**

```python
@app.route('/kpi/<int:record_id>/edit', methods=['GET', 'POST'])
def edit_kpi_record(record_id):
    """编辑KPI记录"""
    record = kpi_db.get_record_by_id(record_id)

    if request.method == 'POST':
        try:
            record.month = request.form.get('month')
            record.product_name = request.form.get('product_name')
            record.actual_quantity = float(request.form.get('actual_quantity')) if request.form.get('actual_quantity') else None
            record.actual_avg_price = float(request.form.get('actual_avg_price')) if request.form.get('actual_avg_price') else None
            record.forecast_quantity = float(request.form.get('forecast_quantity')) if request.form.get('forecast_quantity') else None
            record.forecast_avg_price = float(request.form.get('forecast_avg_price')) if request.form.get('forecast_avg_price') else None

            kpi_db.update_record(record)
            flash('KPI记录更新成功', 'success')
            return redirect(url_for('kpi'))
        except Exception as e:
            flash(f'更新失败: {str(e)}', 'error')

    # GET请求 - 返回JSON用于前端填充表单
    return jsonify(record.to_dict())
```

**Step 5: 添加删除KPI记录路由**

```python
@app.route('/kpi/<int:record_id>/delete', methods=['POST'])
def delete_kpi_record(record_id):
    """删除KPI记录"""
    try:
        kpi_db.delete_record(record_id)
        flash('KPI记录删除成功', 'success')
    except Exception as e:
        flash(f'删除失败: {str(e)}', 'error')

    return redirect(url_for('kpi'))
```

**Step 6: 测试路由加载**

Run: `python3 -c "from app import app; print('路由加载成功')"`
Expected: 输出 "路由加载成功"，无错误

**Step 7: 提交**

```bash
git add app.py
git commit -m "feat: 添加KPI追踪路由"
```

---

## Task 4: 在导航栏添加KPI入口

**Files:**
- Modify: `templates/base.html`

**Step 1: 在导航栏添加KPI链接**

在导航菜单中（约第38行，账务管理链接之后）添加：

```html
<a href="{{ url_for('kpi') }}" class="nav-link {% if request.endpoint in ['kpi', 'new_kpi_record', 'edit_kpi_record'] %}active{% endif %} text-white/90 hover:text-white px-3 py-2 rounded-md text-sm font-medium">
    KPI追踪
</a>
```

**Step 2: 在移动端菜单也添加**

在移动端菜单区域（约第69行）添加：

```html
<a href="{{ url_for('kpi') }}" class="text-white/90 hover:bg-white/10 block px-3 py-2 rounded-md text-base font-medium">KPI追踪</a>
```

**Step 3: 提交**

```bash
git add templates/base.html
git commit -m "feat: 在导航栏添加KPI追踪入口"
```

---

## Task 5: 创建KPI页面模板

**Files:**
- Create: `templates/kpi.html`

**Step 1: 创建KPI页面**

完整的kpi.html模板：

```html
{% extends "base.html" %}

{% block title %}KPI追踪 (A+F) - 期货交易记录系统{% endblock %}

{% block content %}
<div class="md:flex md:items-center md:justify-between mb-6">
    <div class="flex-1 min-w-0">
        <h1 class="text-3xl font-bold text-gray-900">KPI追踪 (A+F)</h1>
        <p class="mt-2 text-gray-600">追踪碳酸锂和氢氧化锂的采购情况，与SMM均价对比计算降本</p>
    </div>
    <div class="mt-4 flex md:mt-0 md:ml-4 space-x-3">
        <button onclick="openFormModal()" class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700">
            <svg class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            添加记录
        </button>
    </div>
</div>

<!-- 统计卡片 -->
<div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
    <!-- 本月实际采购 -->
    <div class="bg-white shadow rounded-lg p-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">本月实际采购</h3>
        <div class="space-y-3">
            {% for product in ['碳酸锂', '氢氧化锂'] %}
                {% if product in stats %}
                <div class="flex justify-between items-center p-3 bg-indigo-50 rounded-lg">
                    <span class="text-sm font-medium text-gray-700">{{ product }}</span>
                    <div class="text-right">
                        <p class="text-lg font-bold text-gray-900">{{ "%.2f"|format(stats[product].total_actual_qty) }} 吨</p>
                        <p class="text-sm text-gray-500">{{ format_unit_price(stats[product].avg_actual_price) }}</p>
                    </div>
                </div>
                {% endif %}
            {% endfor %}
        </div>
    </div>

    <!-- 本月预测 -->
    <div class="bg-white shadow rounded-lg p-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">本月预测</h3>
        <div class="space-y-3">
            {% for product in ['碳酸锂', '氢氧化锂'] %}
                {% if product in stats %}
                <div class="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
                    <span class="text-sm font-medium text-gray-700">{{ product }}</span>
                    <div class="text-right">
                        <p class="text-lg font-bold text-gray-900">{{ "%.2f"|format(stats[product].total_forecast_qty) }} 吨</p>
                        <p class="text-sm text-gray-500">{{ format_unit_price(stats[product].avg_forecast_price) if stats[product].avg_forecast_price else '-' }}</p>
                    </div>
                </div>
                {% endif %}
            {% endfor %}
        </div>
    </div>

    <!-- 降本达成 -->
    <div class="bg-white shadow rounded-lg p-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">降本达成 (vs SMM)</h3>
        <div class="space-y-3">
            {% for product in ['碳酸锂', '氢氧化锂'] %}
                {% if product in stats and stats[product].avg_actual_price %}
                <div class="flex justify-between items-center p-3 {% if stats[product].avg_actual_price %}bg-green-50{% else %}bg-gray-50{% endif %} rounded-lg">
                    <span class="text-sm font-medium text-gray-700">{{ product }}</span>
                    <div class="text-right">
                        {% set smm_price = None %}
                        {% for record in records if record.product_name == product and record.month == current_month %}
                            {% if record.smm_avg_price %}
                                {% set smm_price = record.smm_avg_price %}
                                {% set saving = record.cost_saving %}
                                {% set saving_pct = record.cost_saving_pct %}
                            {% endif %}
                        {% endfor %}
                        {% if smm_price %}
                            {% if saving > 0 %}
                                <p class="text-lg font-bold text-green-600">-{{ format_currency(saving) }}/吨</p>
                                <p class="text-sm text-green-600">{{ "%.2f"|format(saving_pct) }}%</p>
                            {% elif saving < 0 %}
                                <p class="text-lg font-bold text-red-600">+{{ format_currency(abs(saving)) }}/吨</p>
                                <p class="text-sm text-red-600">{{ "%.2f"|format(saving_pct) }}%</p>
                            {% else %}
                                <p class="text-lg font-bold text-gray-600">0.00</p>
                            {% endif %}
                        {% else %}
                            <p class="text-sm text-gray-400">无SMM数据</p>
                        {% endif %}
                    </div>
                </div>
                {% endif %}
            {% endfor %}
        </div>
    </div>
</div>

<!-- 筛选器 -->
<div class="bg-white shadow rounded-lg mb-6">
    <div class="px-4 py-5 sm:p-6">
        <form action="{{ url_for('kpi') }}" method="GET" class="flex flex-wrap gap-4">
            <div>
                <label for="product" class="block text-sm font-medium text-gray-700">品种</label>
                <select name="product" id="product" class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md">
                    <option value="">全部品种</option>
                    {% for product in products %}
                    <option value="{{ product }}" {% if current_product == product %}selected{% endif %}>{{ product }}</option>
                    {% endfor %}
                </select>
            </div>
            <div class="flex items-end gap-2">
                <button type="submit" class="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
                    筛选
                </button>
                <a href="{{ url_for('kpi') }}" class="inline-flex justify-center py-2 px-4 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
                    清除
                </a>
            </div>
        </form>
    </div>
</div>

<!-- KPI记录列表 -->
<div class="bg-white shadow rounded-lg overflow-hidden">
    {% if records %}
    <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
                <tr>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">月份</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">品种</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">实际采购量</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">实际均价</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">预测采购量</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">预测均价</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">SMM均价</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">降本金额</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">降本比例</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">操作</th>
                </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
                {% for record in records %}
                <tr class="hover:bg-gray-50">
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{{ record.month }}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ record.product_name }}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {{ "%.2f"|format(record.actual_quantity) if record.actual_quantity else '-' }}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {{ format_unit_price(record.actual_avg_price) if record.actual_avg_price else '-' }}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {{ "%.2f"|format(record.forecast_quantity) if record.forecast_quantity else '-' }}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {{ format_unit_price(record.forecast_avg_price) if record.forecast_avg_price else '-' }}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {{ format_unit_price(record.smm_avg_price) if record.smm_avg_price else '<span class="text-gray-400">无数据</span>'|safe }}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium
                        {% if record.cost_saving is not none %}
                            {% if record.cost_saving > 0 %}text-green-600
                            {% elif record.cost_saving < 0 %}text-red-600
                            {% else %}text-gray-600
                            {% endif %}
                        {% else %}text-gray-400
                        {% endif %}">
                        {% if record.cost_saving is not none %}
                            {% if record.cost_saving > 0 %}-{{ format_currency(record.cost_saving) }}
                            {% elif record.cost_saving < 0 %}+{{ format_currency(abs(record.cost_saving)) }}
                            {% else %}0.00
                            {% endif %}
                        {% else %}-{% endif %}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium
                        {% if record.cost_saving_pct is not none %}
                            {% if record.cost_saving_pct > 0 %}text-green-600
                            {% elif record.cost_saving_pct < 0 %}text-red-600
                            {% else %}text-gray-600
                            {% endif %}
                        {% else %}text-gray-400
                        {% endif %}">
                        {% if record.cost_saving_pct is not none %}
                            {% if record.cost_saving_pct > 0 %}{{ "%.2f"|format(record.cost_saving_pct) }}%
                            {% elif record.cost_saving_pct < 0 %}{{ "%.2f"|format(record.cost_saving_pct) }}%
                            {% else %}0.00%
                            {% endif %}
                        {% else %}-{% endif %}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                        <button onclick="editRecord({{ record.id }})" class="text-indigo-600 hover:text-indigo-900">编辑</button>
                        <form action="{{ url_for('delete_kpi_record', record_id=record.id) }}" method="POST" class="inline" onsubmit="return confirm('确定要删除这条记录吗？');">
                            <button type="submit" class="text-red-600 hover:text-red-900">删除</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% else %}
    <div class="px-4 py-12 text-center">
        <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <h3 class="mt-2 text-sm font-medium text-gray-900">暂无KPI记录</h3>
        <p class="mt-1 text-sm text-gray-500">开始添加KPI追踪记录吧</p>
        <div class="mt-6">
            <button onclick="openFormModal()" class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700">
                添加第一条记录
            </button>
        </div>
    </div>
    {% endif %}
</div>

<!-- 添加/编辑表单模态框 -->
<div id="formModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full hidden">
    <div class="relative top-20 mx-auto p-5 border w-full max-w-lg shadow-lg rounded-md bg-white">
        <div class="flex justify-between items-center mb-4">
            <h3 id="modalTitle" class="text-lg font-medium text-gray-900">添加KPI记录</h3>
            <button onclick="closeFormModal()" class="text-gray-400 hover:text-gray-500">
                <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
            </button>
        </div>
        <form id="kpiForm" action="{{ url_for('new_kpi_record') }}" method="POST" class="space-y-4">
            <input type="hidden" id="recordId" name="id" value="">

            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label for="month" class="block text-sm font-medium text-gray-700">月份 *</label>
                    <input type="month" id="month" name="month" required
                           class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
                </div>
                <div>
                    <label for="product_name" class="block text-sm font-medium text-gray-700">品种 *</label>
                    <select id="product_name" name="product_name" required
                            class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md">
                        <option value="">请选择</option>
                        <option value="碳酸锂">碳酸锂</option>
                        <option value="氢氧化锂">氢氧化锂</option>
                    </select>
                </div>
            </div>

            <div class="border-t border-gray-200 pt-4">
                <h4 class="text-sm font-medium text-gray-700 mb-3">实际数据 (Actual)</h4>
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label for="actual_quantity" class="block text-sm font-medium text-gray-700">采购量（吨）</label>
                        <input type="number" id="actual_quantity" name="actual_quantity" step="0.01" min="0"
                               class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
                    </div>
                    <div>
                        <label for="actual_avg_price" class="block text-sm font-medium text-gray-700">均价（元/吨）</label>
                        <input type="number" id="actual_avg_price" name="actual_avg_price" step="0.01" min="0"
                               class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
                    </div>
                </div>
            </div>

            <div class="border-t border-gray-200 pt-4">
                <h4 class="text-sm font-medium text-gray-700 mb-3">预测数据 (Forecast)</h4>
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label for="forecast_quantity" class="block text-sm font-medium text-gray-700">预测量（吨）</label>
                        <input type="number" id="forecast_quantity" name="forecast_quantity" step="0.01" min="0"
                               class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
                    </div>
                    <div>
                        <label for="forecast_avg_price" class="block text-sm font-medium text-gray-700">预测均价（元/吨）</label>
                        <input type="number" id="forecast_avg_price" name="forecast_avg_price" step="0.01" min="0"
                               class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
                    </div>
                </div>
            </div>

            <div class="flex justify-end space-x-3 pt-4 border-t">
                <button type="button" onclick="closeFormModal()" class="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400">取消</button>
                <button type="submit" class="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700">保存</button>
            </div>
        </form>
    </div>
</div>

<script>
function openFormModal() {
    document.getElementById('modalTitle').textContent = '添加KPI记录';
    document.getElementById('kpiForm').action = "{{ url_for('new_kpi_record') }}";
    document.getElementById('kpiForm').reset();
    document.getElementById('recordId').value = '';
    document.getElementById('formModal').classList.remove('hidden');
}

function closeFormModal() {
    document.getElementById('formModal').classList.add('hidden');
}

async function editRecord(recordId) {
    try {
        const response = await fetch(`{{ url_for('edit_kpi_record', record_id=0) }}`.replace('0', recordId));
        const record = await response.json();

        document.getElementById('modalTitle').textContent = '编辑KPI记录';
        document.getElementById('kpiForm').action = `{{ url_for('edit_kpi_record', record_id=0) }}`.replace('0', recordId);
        document.getElementById('recordId').value = record.id;
        document.getElementById('month').value = record.month;
        document.getElementById('product_name').value = record.product_name;
        document.getElementById('actual_quantity').value = record.actual_quantity || '';
        document.getElementById('actual_avg_price').value = record.actual_avg_price || '';
        document.getElementById('forecast_quantity').value = record.forecast_quantity || '';
        document.getElementById('forecast_avg_price').value = record.forecast_avg_price || '';

        document.getElementById('formModal').classList.remove('hidden');
    } catch (error) {
        console.error('加载记录失败:', error);
        alert('加载记录失败');
    }
}

// 点击模态框外部关闭
document.getElementById('formModal').addEventListener('click', function(e) {
    if (e.target === this) {
        closeFormModal();
    }
});
</script>
{% endblock %}
```

**Step 2: 验证模板创建**

Run: `ls -la /Users/niuniu/cc/futures_trading_journal/templates/kpi.html`
Expected: 文件存在

**Step 3: 提交**

```bash
git add templates/kpi.html
git commit -m "feat: 创建KPI追踪页面模板"
```

---

## Task 6: 添加E2E测试

**Files:**
- Create: `tests/e2e/kpi.spec.ts`

**Step 1: 创建KPI E2E测试文件**

```typescript
import { test, expect } from '@playwright/test';

test.describe('KPI追踪功能', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/kpi');
  });

  test('显示KPI页面标题', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('KPI追踪');
  });

  test('显示统计卡片', async ({ page }) => {
    await expect(page.locator('text=本月实际采购')).toBeVisible();
    await expect(page.locator('text=本月预测')).toBeVisible();
    await expect(page.locator('text=降本达成')).toBeVisible();
  });

  test('打开添加记录模态框', async ({ page }) => {
    await page.click('button:has-text("添加记录")');
    await expect(page.locator('#formModal')).toBeVisible();
    await expect(page.locator('#modalTitle')).toContainText('添加KPI记录');
  });

  test('品种筛选功能', async ({ page }) => {
    await page.selectOption('#product', '碳酸锂');
    await page.click('button:has-text("筛选")');
    // 验证URL包含筛选参数
    expect(page.url()).toContain('product=碳酸锂');
  });

  test('添加新KPI记录', async ({ page }) => {
    await page.click('button:has-text("添加记录")');

    // 填写表单
    await page.fill('#month', '2026-03');
    await page.selectOption('#product_name', '碳酸锂');
    await page.fill('#actual_quantity', '100');
    await page.fill('#actual_avg_price', '150000');
    await page.fill('#forecast_quantity', '120');
    await page.fill('#forecast_avg_price', '148000');

    // 提交表单
    await page.click('button:has-text("保存")');

    // 验证重定向回列表页
    await expect(page).toHaveURL('/kpi');
  });

  test('编辑KPI记录', async ({ page }) => {
    // 假设列表中至少有一条记录
    const editButton = page.locator('button:has-text("编辑")').first();
    if (await editButton.isVisible()) {
      await editButton.click();
      await expect(page.locator('#formModal')).toBeVisible();
      await expect(page.locator('#modalTitle')).toContainText('编辑KPI记录');
    }
  });

  test('删除KPI记录', async ({ page }) => {
    // 假设列表中至少有一条记录
    const deleteForm = page.locator('form.inline').first();
    if (await deleteForm.isVisible()) {
      // 监听对话框
      page.on('dialog', dialog => {
        expect(dialog.message()).toContain('确定要删除');
        dialog.accept();
      });

      await deleteForm.locator('button:has-text("删除")').click();
    }
  });
});
```

**Step 2: 运行E2E测试**

Run: `npx playwright test tests/e2e/kpi.spec.ts`
Expected: 测试通过（可能需要先启动应用）

**Step 3: 提交**

```bash
git add tests/e2e/kpi.spec.ts
git commit -m "test: 添加KPI追踪E2E测试"
```

---

## 完成验证

**Step 1: 启动应用**

Run: `python3 app.py`

**Step 2: 手动测试功能**

1. 访问 http://localhost:5000/kpi
2. 点击"添加记录"按钮
3. 填写表单并提交
4. 验证记录显示在列表中
5. 验证SMM价格自动获取
6. 验证降本计算正确

**Step 3: 最终提交**

```bash
git add .
git commit -m "feat: 完成KPI追踪功能开发"
```
