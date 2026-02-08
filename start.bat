@echo off
chcp 65001 >nul
title 期货交易记录系统

echo ===================================
echo   期货交易记录系统
echo ===================================
echo.

:: 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.8或更高版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 检查虚拟环境是否存在
if not exist "venv\" (
    echo [信息] 首次运行，正在创建虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败
        pause
        exit /b 1
    )
    echo [成功] 虚拟环境创建完成
)

:: 激活虚拟环境
call venv\Scripts\activate.bat

:: 安装依赖
echo [信息] 检查并安装依赖包...
pip install -r requirements.txt -q

:: 创建必要的目录
if not exist "data\" mkdir data
if not exist "exports\" mkdir exports
if not exist "static\css\" mkdir static\css
if not exist "static\js\" mkdir static\js

:: 启动应用
echo.
echo [成功] 正在启动期货交易记录系统...
echo.
echo 访问地址: http://localhost:5000
echo 按 Ctrl+C 可以停止服务器
echo.
python app.py

pause
