#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# 安防维保管理系统 — Termux 启动脚本
# ============================================================
# 在手机浏览器访问: http://localhost:5001
# 局域网其他设备访问: http://<手机IP>:5001
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 启动前默认生成数据库
python3 -c "
from database import Database
db = Database()
db.init_db()
print('✅ 数据库就绪')
" 2>/dev/null

echo "=========================================="
echo "  安防维保管理系统 — 启动中..."
echo "=========================================="
echo ""

# 启动 Flask 服务（使用 waitress 替代 gunicorn，Windows/Android 兼容）
# 如果安装了 gunicorn 则使用 gunicorn，否则用 waitress
if command -v gunicorn &>/dev/null; then
    echo "启动服务 (gunicorn)..."
    echo "  手机:  http://localhost:5001"
    echo "  局域网: http://$(ifconfig 2>/dev/null | grep -oP 'inet \K[\d.]+' | grep -v '127.0.0.1' | head -1):5001"
    echo ""
    gunicorn --bind "0.0.0.0:5001" --workers 2 --threads 4 --timeout 120 app:app
else
    echo "安装 waitress..."
    pip install waitress -q
    echo "启动服务 (waitress)..."
    echo "  手机:  http://localhost:5001"
    echo "  局域网: http://$(ifconfig 2>/dev/null | grep -oP 'inet \K[\d.]+' | grep -v '127.0.0.1' | head -1):5001"
    echo ""
    python3 -c "
from waitress import serve
from app import app
print('  按 Ctrl+C 停止服务')
serve(app, host='0.0.0.0', port=5001, threads=4)
"
fi
