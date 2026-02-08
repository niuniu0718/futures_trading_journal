@echo off
chcp 65001 >nul
echo ================================
echo 期货交易记录系统 - 安装依赖
echo ================================
echo.

echo 正在检查Python版本...
python --version
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.8或更高版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo.
echo 正在安装依赖包...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

if errorlevel 1 (
    echo.
    echo [警告] 清华源安装失败，尝试使用默认源...
    pip install -r requirements.txt
)

if errorlevel 1 (
    echo.
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)

echo.
echo ================================
echo 安装完成！
echo ================================
echo.
echo 运行 start.bat 启动系统
echo.
pause
