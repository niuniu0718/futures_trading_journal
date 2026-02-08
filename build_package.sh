#!/bin/bash
# 打包脚本

VERSION="v1.1.0"
DATE=$(date +%Y%m%d)
PACKAGE_NAME="futures_trading_journal_${VERSION}_${DATE}"
TEMP_DIR="/tmp/${PACKAGE_NAME}"

echo "========================================"
echo "期货交易记录系统 - 打包脚本"
echo "版本: ${VERSION}"
echo "========================================"
echo

# 创建临时目录
echo "[1/6] 创建临时目录..."
rm -rf "${TEMP_DIR}"
mkdir -p "${TEMP_DIR}"

# 复制文件
echo "[2/6] 复制项目文件..."
cp -r . "${TEMP_DIR}/"

# 删除不需要的文件
echo "[3/6] 清理不必要的文件..."
cd "${TEMP_DIR}"
rm -rf __pycache__
rm -rf *.pyc
rm -rf .git
rm -rf .claude
rm -rf *.egg-info
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null

# 创建空的data目录
echo "[4/6] 创建数据目录..."
mkdir -p data
touch data/.gitkeep

# 创建Windows启动脚本
echo "[5/6] 创建Windows启动脚本..."
cat > "启动系统.bat" << 'EOF'
@echo off
chcp 65001
echo ================================
echo 期货交易记录系统 启动脚本
echo ================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到Python，请先安装Python 3.8或更高版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] 检查依赖...
pip show flask >nul 2>&1
if %errorlevel% neq 0 (
    echo [提示] 检测到缺少依赖，正在自动安装...
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if %errorlevel% neq 0 (
        echo [错误] 依赖安装失败，请检查网络连接
        pause
        exit /b 1
    )
) else (
    echo [成功] 依赖已安装
)

echo.
echo [2/3] 初始化数据库...
python -c "from database import db; print('数据库初始化完成')" 2>nul
if %errorlevel% neq 0 (
    echo [错误] 数据库初始化失败
    pause
    exit /b 1
)

echo.
echo [3/3] 启动服务器...
echo.
echo 访问地址: http://localhost:5000
echo 按 Ctrl+C 停止服务器
echo.
echo ================================
echo.

python app.py

pause
EOF

# 创建zip包
echo "[6/6] 创建压缩包..."
cd /tmp
zip -rq "${PACKAGE_NAME}.zip" "${PACKAGE_NAME}"

# 移动到当前目录
mv "${PACKAGE_NAME}.zip" "/Users/niuniu/cc/futures_trading_journal/"

# 清理临时目录
rm -rf "${TEMP_DIR}"

echo
echo "========================================"
echo "打包完成！"
echo "文件名: ${PACKAGE_NAME}.zip"
echo "位置: /Users/niuniu/cc/futures_trading_journal/"
echo "========================================"
ls -lh "/Users/niuniu/cc/futures_trading_journal/${PACKAGE_NAME}.zip"
