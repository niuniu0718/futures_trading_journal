#!/bin/bash

# 期货交易记录系统 - 启动脚本

echo "========================================="
echo "期货交易记录系统"
echo "========================================="
echo ""

# 检查Python版本
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python3"
    echo "请先安装 Python 3.7 或更高版本"
    exit 1
fi

echo "✅ Python 已安装"

# 检查依赖
echo ""
echo "📦 检查依赖..."
python3 -m pip install -r requirements.txt -q 2>&1 | tail -1

# 检查数据目录
echo ""
echo "📁 检查目录结构..."
mkdir -p data exports static/{css,js} templates

echo ""
echo "========================================="
echo "🚀 启动应用..."
echo "========================================="
echo ""
echo "访问地址: http://localhost:5000"
echo "按 Ctrl+C 停止服务器"
echo ""

# 启动应用
python3 app.py
