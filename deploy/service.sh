#!/bin/bash
# Stock V2 服务管理脚本（部署在服务器上）
# 用法: service.sh [start|stop|restart|status]

set -e

APP_DIR="/opt/stock_v2"
BACKEND_DIR="$APP_DIR/backend"
PID_FILE="$APP_DIR/app.pid"
LOG_FILE="$APP_DIR/logs/backend.log"
PORT=38080

mkdir -p "$APP_DIR/logs" "$APP_DIR/data"

get_pid() {
    [ -f "$PID_FILE" ] && cat "$PID_FILE" 2>/dev/null || echo ""
}

is_running() {
    local pid=$(get_pid)
    [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

start() {
    if is_running; then
        echo "服务已在运行 (PID: $(get_pid))"
        return 0
    fi

    echo "启动 Stock V2..."
    cd "$BACKEND_DIR"
    nohup .venv/bin/python -m app.main > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"

    # 等待端口就绪
    for i in $(seq 1 15); do
        if lsof -ti :$PORT >/dev/null 2>&1; then
            echo "启动成功 (PID: $(get_pid))"
            return 0
        fi
        sleep 1
    done

    echo "启动超时，请查看日志: $LOG_FILE"
    return 1
}

stop() {
    local pid=$(get_pid)
    if [ -z "$pid" ] || ! is_running; then
        echo "服务未运行"
        rm -f "$PID_FILE"
        return 0
    fi

    echo "停止服务 (PID: $pid)..."
    kill "$pid" 2>/dev/null || true
    sleep 1

    # 强制停止
    if is_running; then
        kill -9 "$pid" 2>/dev/null || true
    fi

    rm -f "$PID_FILE"
    echo "已停止"
}

restart() {
    stop
    sleep 1
    start
}

status() {
    if is_running; then
        echo "运行中 (PID: $(get_pid), 端口: $PORT)"
    else
        echo "未运行"
    fi
}

case "${1:-help}" in
    start)   start ;;
    stop)    stop ;;
    restart) restart ;;
    status)  status ;;
    *)
        echo "用法: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
