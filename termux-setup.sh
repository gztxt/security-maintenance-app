#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# 安防维保管理系统 — Termux 一键部署脚本
# ============================================================
# 使用方法：
#   1. 将此文件夹放到手机 Termux 的 ~/storage/shared/ 下
#   2. 执行: bash termux-setup.sh
#   3. 安装完成后，执行: bash start-app.sh
#   4. 打开 Chrome → localhost:5001 → 添加到主屏幕
# ============================================================

set -e

echo "=========================================="
echo "  安防维保管理系统 - Termux 部署脚本"
echo "=========================================="
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 1. 更新包管理器
echo "[1/6] 更新 Termux 包管理器..."
pkg update -y && pkg upgrade -y

# 2. 安装 Python 和基础工具
echo "[2/6] 安装 Python 和依赖..."
pkg install -y python python-pip git

# 3. 安装图片处理依赖（reportlab + pillow 需要）
echo "[3/6] 安装系统库..."
pkg install -y freetype libpng libjpeg-turbo

# 4. 安装 Python 包
echo "[4/6] 安装 Python 包..."
pip install --upgrade pip
pip install flask flask-cors gunicorn pillow reportlab PyPDF2

# 5. 下载中文字体
echo "[5/6] 配置中文字体..."
FONT_DIR="$PREFIX/share/fonts"
mkdir -p "$FONT_DIR"
# DroidSansFallbackFull.ttf - 从 Termux 字体包或网上下载
# 如果 Termux 已安装字体则直接使用
FONT_SRC=$(find /system/fonts /data/fonts "$PREFIX/share" -name "DroidSansFallback*" 2>/dev/null | head -1)
if [ -n "$FONT_SRC" ]; then
    echo "  发现系统字体: $FONT_SRC"
    cp "$FONT_SRC" "$SCRIPT_DIR/"
else
    echo "  尝试下载中文字体..."
    # 从 github 下载合并字体
    curl -L -o "DroidSansFallbackFull.ttf" \
        "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/zh-hans/NotoSansCJKsc-Regular.otf" 2>/dev/null || \
    curl -L -o "DroidSansFallbackFull.ttf" \
        "https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/zh-hans/NotoSansCJKsc-Regular.otf" 2>/dev/null || \
    echo "  ⚠️ 字体下载失败，需手动放入 DroidSansFallbackFull.ttf"
fi

# 6. 初始化数据库
echo "[6/6] 初始化数据库..."
python3 -c "
from database import Database
db = Database()
db.init_db()
print('  ✅ 数据库初始化成功')
"

echo ""
echo "=========================================="
echo "  ✅ 部署完成！"
echo "=========================================="
echo ""
echo "启动方式:"
echo "  bash start-app.sh"
echo ""
echo "访问地址:"
echo "  http://localhost:5001"
echo ""
echo "设置为桌面图标:"
echo "  1. 打开 Chrome → 访问 localhost:5001"
echo "  2. 右上角菜单 → 添加到主屏幕"
echo "=========================================="
