#!/bin/bash
cd /fs/1000/ftp/技术文档/安防维保管理系统
source venv/bin/activate
PORT=5001
HOST=::

# 停止旧进程
if [ -f /tmp/security-maintenance.pid ]; then
    OLD_PID=$(cat /tmp/security-maintenance.pid)
    kill "$OLD_PID" 2>/dev/null
    sleep 1
fi

# 用 gunicorn 启动（生产级，稳定不自杀）
nohup venv/bin/gunicorn \
    --bind "[::]:$PORT" \
    --workers 2 \
    --threads 4 \
    --timeout 120 \
    --access-logfile /tmp/security-maintenance-access.log \
    --error-logfile /tmp/security-maintenance-error.log \
    --pid /tmp/security-maintenance.pid \
    --daemon \
    app:app

echo "安防维保管理系统已启动 - PID: $(cat /tmp/security-maintenance.pid)"
echo "监听: [::]:$PORT"
echo "访问: http://192.168.5.102:$PORT"
