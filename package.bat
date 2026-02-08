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
