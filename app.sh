#!/bin/bash
# Stock V2 管理脚本
# 用法: ./app.sh [start|stop|status|restart|logs]

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
LOG_DIR="$PROJECT_DIR/logs"
DB_FILE="$PROJECT_DIR/data/stock_v2.db"

BACKEND_PORT=38080
FRONTEND_PORT=35173

mkdir -p "$LOG_DIR"

# ── 端口工具函数 ──

port_pids() {
    # 返回占用指定端口的所有进程PID
    lsof -ti :"$1" 2>/dev/null || true
}

kill_port() {
    # 杀掉占用指定端口的所有进程（含子进程）
    local pids
    pids=$(port_pids "$1")
    if [ -n "$pids" ]; then
        echo "$pids" | xargs kill -9 2>/dev/null || true
        sleep 0.5
        # 二次检查，杀残留
        pids=$(port_pids "$1")
        [ -n "$pids" ] && echo "$pids" | xargs kill -9 2>/dev/null || true
    fi
}

port_status() {
    # 返回端口状态: "running" 或 "free"
    if port_pids "$1" | grep -q .; then
        echo "running"
    else
        echo "free"
    fi
}

# ── 命令 ──

cmd_start() {
    local mode="${1:-dev}"

    echo "=== Stock V2 启动 ($mode 模式) ==="

    # 检查端口占用
    if [ "$(port_status $BACKEND_PORT)" = "running" ]; then
        echo "  端口 $BACKEND_PORT 已被占用，先停止旧进程..."
        kill_port $BACKEND_PORT
    fi
    if [ "$(port_status $FRONTEND_PORT)" = "running" ]; then
        echo "  端口 $FRONTEND_PORT 已被占用，先停止旧进程..."
        kill_port $FRONTEND_PORT
    fi

    # 后端
    echo "[1/2] 启动后端(:$BACKEND_PORT)..."
    cd "$BACKEND_DIR"
    if [ ! -d "venv" ]; then
        echo "  创建虚拟环境..."
        python3 -m venv venv
    fi
    source venv/bin/activate
    if [ ! -f "venv/.installed" ] || [ "requirements.txt" -nt "venv/.installed" ]; then
        echo "  安装依赖..."
        pip install -r requirements.txt -q
        touch venv/.installed
    fi
    mkdir -p "$PROJECT_DIR/data"
    nohup python -m app.main > "$LOG_DIR/backend.log" 2>&1 &

    # 等待端口就绪
    echo "  等待后端就绪..."
    for i in $(seq 1 15); do
        if [ "$(port_status $BACKEND_PORT)" = "running" ]; then
            echo "  后端就绪 ✓"
            break
        fi
        [ "$i" = "15" ] && echo "  后端启动超时，请查看日志: ./app.sh logs"
        sleep 1
    done

    # 前端
    echo "[2/2] 启动前端(:$FRONTEND_PORT)..."
    cd "$FRONTEND_DIR"
    if [ ! -d "node_modules" ]; then
        echo "  安装依赖..."
        npm install -q
    fi
    if [ "$mode" = "prod" ]; then
        npm run build
        echo "  前端已构建: $FRONTEND_DIR/dist/"
    else
        nohup npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
        sleep 2
        echo "  前端就绪 ✓"
    fi

    echo ""
    echo "=== 启动完成 ==="
    echo "  后端API: http://localhost:$BACKEND_PORT"
    echo "  API文档: http://localhost:$BACKEND_PORT/docs"
    [ "$mode" != "prod" ] && echo "  前端:    http://localhost:$FRONTEND_PORT"
    echo "  停止:    ./app.sh stop"
}

cmd_stop() {
    echo "=== Stock V2 停止 ==="

    if [ "$(port_status $BACKEND_PORT)" = "running" ]; then
        local pids=$(port_pids $BACKEND_PORT)
        kill_port $BACKEND_PORT
        echo "  后端(:$BACKEND_PORT) 已停止 (PIDs: $pids)"
    else
        echo "  后端(:$BACKEND_PORT) 未运行"
    fi

    if [ "$(port_status $FRONTEND_PORT)" = "running" ]; then
        local pids=$(port_pids $FRONTEND_PORT)
        kill_port $FRONTEND_PORT
        echo "  前端(:$FRONTEND_PORT) 已停止 (PIDs: $pids)"
    else
        echo "  前端(:$FRONTEND_PORT) 未运行"
    fi
}

cmd_status() {
    echo "=== Stock V2 状态 ==="

    # 后端
    if [ "$(port_status $BACKEND_PORT)" = "running" ]; then
        local pids=$(port_pids $BACKEND_PORT | tr '\n' ',' | sed 's/,$//')
        echo "  后端(:$BACKEND_PORT): 运行中 (PIDs: $pids)"
    else
        echo "  后端(:$BACKEND_PORT): 未运行"
    fi

    # 前端
    if [ "$(port_status $FRONTEND_PORT)" = "running" ]; then
        local pids=$(port_pids $FRONTEND_PORT | tr '\n' ',' | sed 's/,$//')
        echo "  前端(:$FRONTEND_PORT): 运行中 (PIDs: $pids)"
    else
        echo "  前端(:$FRONTEND_PORT): 未运行"
    fi

    # 数据库
    [ -f "$DB_FILE" ] && echo "  数据库: $(du -h "$DB_FILE" | cut -f1)" || echo "  数据库: 未创建"
}

cmd_logs() {
    local target="${1:-backend}"
    local logfile="$LOG_DIR/$target.log"
    if [ -f "$logfile" ]; then
        tail -f "$logfile"
    else
        echo "日志文件不存在: $logfile"
        exit 1
    fi
}

# ── 主入口 ──
case "${1:-help}" in
    start)   cmd_start "${2:-dev}" ;;
    stop)    cmd_stop ;;
    restart) cmd_stop; sleep 1; cmd_start "${2:-dev}" ;;
    status)  cmd_status ;;
    logs)    cmd_logs "${2:-backend}" ;;
    *)
        echo "用法: ./app.sh <命令>"
        echo ""
        echo "命令:"
        echo "  start [dev|prod]   启动（默认dev）"
        echo "  stop               停止"
        echo "  restart [dev|prod] 重启"
        echo "  status             查看状态"
        echo "  logs [backend|frontend] 查看日志"
        echo ""
        echo "端口: 后端:$BACKEND_PORT 前端:$FRONTEND_PORT"
        ;;
esac
