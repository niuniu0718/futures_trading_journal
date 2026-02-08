# 期货交易记录系统

一个完整的期货交易记录和管理系统，用于记录每天的交易、分析市场走势，并提供统计分析和图表展示。

## 功能特性

- ✅ 交易记录管理（增删改查）
- ✅ 多空方向支持（多单/空单）
- ✅ 技术指标记录（MA5/MA10/MA20、RSI、MACD）
- ✅ 市场走势分析
- ✅ 平仓操作与自动盈亏计算
- ✅ 统计分析（胜率、盈亏比、最大回撤等）
- ✅ 图表展示（累计盈亏、品种表现、价格走势）
- ✅ 数据导入导出（CSV格式）
- ✅ 响应式设计

## 技术栈

- **后端**: Flask + SQLite + Pandas
- **前端**: Tailwind CSS + Chart.js + Alpine.js
- **日志**: Loguru

## 安装运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行应用

```bash
python app.py
```

### 3. 访问系统

打开浏览器访问: http://localhost:5000

## 项目结构

```
futures_trading_journal/
├── app.py                 # Flask应用主入口
├── models.py              # 数据模型
├── database.py            # 数据库管理
├── analyzers.py           # 统计分析模块
├── utils.py              # 工具函数
├── config.py             # 配置文件
├── static/
│   ├── css/style.css     # 自定义样式
│   └── js/app.js         # 前端交互
├── templates/
│   ├── base.html         # 基础模板
│   ├── index.html        # 首页仪表盘
│   ├── trades.html       # 交易记录列表
│   ├── trade_form.html   # 新建/编辑交易
│   └── statistics.html   # 统计分析页面
├── data/
│   └── trading_journal.db # SQLite数据库
└── exports/              # 导出文件目录
```

## 使用说明

### 添加交易记录

1. 点击"新建交易"按钮
2. 填写交易信息：
   - 基础信息：日期、交易所、品种、合约、方向、数量
   - 价格信息：开仓价、止损价、止盈价、手续费
   - 技术指标：MA5/MA10/MA20、RSI、MACD
   - 市场分析：走势判断、入场理由、交易备注
3. 点击"创建"保存

### 平仓操作

1. 在交易列表中找到持仓中的交易
2. 点击"平仓"按钮
3. 填写平仓价格和日期
4. 系统自动计算盈亏

### 查看统计

访问"统计分析"页面查看：
- 基础统计（总交易数、胜率等）
- 盈亏统计（总盈亏、最大盈亏）
- 风险指标（最大回撤、盈亏比、期望值）
- 多空方向统计
- 各类图表展示

### 数据导入导出

- **导出**: 点击交易列表页面的"导出"按钮
- **导入**: 点击"导入"按钮选择CSV文件

## 数据模型

### 交易记录字段

| 字段 | 说明 |
|------|------|
| trade_date | 交易日期 |
| exchange | 交易所 |
| product_name | 品种名称 |
| contract | 合约代码 |
| direction | 方向 (long/short) |
| entry_price | 开仓价格 |
| quantity | 数量 |
| stop_loss | 止损价格 |
| take_profit | 止盈价格 |
| exit_price | 平仓价格 |
| exit_date | 平仓日期 |
| fee | 手续费 |
| profit_loss | 盈亏金额 |
| status | 状态 (open/closed) |
| ma5/ma10/ma20 | 移动平均线指标 |
| rsi | RSI指标 |
| macd | MACD指标 |
| entry_reason | 入场理由 |
| market_trend | 市场走势 |
| notes | 交易日志 |

## API接口

- `GET /` - 首页仪表盘
- `GET /trades` - 交易列表
- `GET/POST /trades/new` - 新建交易
- `GET/POST /trades/<id>/edit` - 编辑交易
- `POST /trades/<id>/delete` - 删除交易
- `POST /trades/<id>/close` - 平仓操作
- `GET /statistics` - 统计分析
- `GET /api/trades` - 获取交易数据（JSON）
- `GET /api/statistics` - 获取统计数据（JSON）
- `GET /export/csv` - 导出CSV
- `POST /import` - 导入数据

## 注意事项

1. 本系统仅供学习交流使用，不构成任何投资建议
2. 期货交易有风险，投资需谨慎
3. 建议定期备份数据库文件

## 许可证

MIT License
