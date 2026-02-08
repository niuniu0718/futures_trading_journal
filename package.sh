#!/bin/bash

# 期货交易记录系统 - 打包脚本
# 用于创建Windows可运行的压缩包

echo "===================================="
echo "  期货交易记录系统 - 打包工具"
echo "===================================="
echo ""

# 设置变量
APP_NAME="期货交易记录系统"
VERSION="1.2.0"
TODAY=$(date +%Y%m%d)
PACKAGE_DIR="package_temp"
ZIP_FILE="期货交易记录系统-${TODAY}-v${VERSION}.zip"

# 清理旧的打包文件
echo "[1/5] 清理旧文件..."
rm -f "${ZIP_FILE}"
rm -rf "${PACKAGE_DIR}"
mkdir -p "${PACKAGE_DIR}"

# 复制必要的文件
echo "[2/5] 复制应用文件..."
cp -r \
    app.py \
    models.py \
    database.py \
    physical_model.py \
    config.py \
    analyzers.py \
    utils.py \
    requirements.txt \
    templates/ \
    static/ \
    "${PACKAGE_DIR}/"

# 创建必要的目录结构
echo "[3/5] 创建目录结构..."
mkdir -p "${PACKAGE_DIR}/data"
mkdir -p "${PACKAGE_DIR}/exports"

# 复制Windows启动脚本
echo "[4/5] 添加启动脚本..."
cp start.bat "${PACKAGE_DIR}/"

# 创建README
echo "[5/5] 创建说明文档..."
cat > "${PACKAGE_DIR}/README.txt" << 'README_EOF'
========================================
   期货交易记录系统 v1.0.0
   Windows 使用说明
========================================

【快速启动】

1. 双击运行 start.bat
2. 首次运行会自动安装依赖（需要几分钟）
3. 安装完成后会自动启动系统
4. 在浏览器中访问: http://localhost:5000


【系统要求】

- Windows 7/8/10/11
- Python 3.8 或更高版本
  如果没有安装Python，请访问:
  https://www.python.org/downloads/
  
  安装时请勾选 "Add Python to PATH"


【主要功能】

1. 交易记录管理
   - 添加、编辑、删除期货交易记录
   - 支持多空方向、止损止盈设置
   - 平仓自动计算盈亏

2. 统计分析
   - 总盈亏、胜率、盈亏比统计
   - 按品种、月份、方向分析
   - 风险指标分析

3. SMM价格管理
   - 录入SMM月度价格
   - 对比期货与SMM价格折扣

4. 实物采购管理
   - 记录实物采购信息
   - 关联期货保值头寸
   - 贴水计算

5. 数据导入导出
   - 导出为Excel/CSV
   - 数据备份恢复


【目录结构】

期货交易记录系统/
├── start.bat          # Windows启动脚本（双击运行）
├── app.py             # 主程序
├── models.py          # 数据模型
├── database.py        # 数据库管理
├── physical_model.py  # 实物采购模型
├── config.py          # 配置文件
├── requirements.txt   # 依赖包列表
├── templates/         # 网页模板
├── static/           # 静态资源
├── data/             # 数据库文件（自动创建）
└── exports/          # 导出文件目录（自动创建）


【常见问题】

Q: 双击start.bat后闪退？
A: 请确保已安装Python并添加到PATH环境变量

Q: 如何停止服务器？
A: 在命令行窗口按 Ctrl+C

Q: 数据存储在哪里？
A: 所有数据存储在 data/trading_journal.db 文件中

Q: 如何备份数据？
A: 复制 data/trading_journal.db 文件即可

Q: 端口5000被占用怎么办？
A: 编辑 app.py 文件，修改最后一行的端口号


【技术支持】

如遇问题，请检查：
1. Python版本是否为3.8或更高
2. 网络连接是否正常（首次需要下载依赖）
3. 是否有管理员权限


========================================
© 2026 期货交易记录系统
========================================
README_EOF

# 创建压缩包
echo ""
echo "[完成] 创建压缩包..."
cd "${PACKAGE_DIR}"
zip -r "../${ZIP_FILE}" * > /dev/null
cd ..

# 清理临时文件
rm -rf "${PACKAGE_DIR}"

echo ""
echo "===================================="
echo "  打包完成！"
echo "===================================="
echo ""
echo "压缩包名称: ${ZIP_FILE}"
echo "文件大小: $(du -h "${ZIP_FILE}" | cut -f1)"
echo ""
echo "用户使用说明："
echo "1. 解压 ${ZIP_FILE}"
echo "2. 双击运行 start.bat"
echo "3. 在浏览器访问 http://localhost:5000"
echo ""
