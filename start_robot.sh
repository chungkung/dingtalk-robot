#!/bin/bash
echo "========================================"
echo "  IT管理部智能助手 - 一键启动"
echo "========================================"
echo ""

REPO_URL="https://github.com/chungkung/dingtalk-robot.git"
LOCAL_DIR="$HOME/dingtalk-robot"

if ! command -v python &> /dev/null; then
    echo "[错误] 未检测到Python，请先安装Python 3.8+"
    exit 1
fi

if [ -d "$LOCAL_DIR" ]; then
    echo "[1/4] 发现已有代码，检查更新..."
    cd "$LOCAL_DIR"
    git pull origin master
else
    echo "[1/4] 正在从GitHub下载代码..."
    cd $HOME
    git clone $REPO_URL dingtalk-robot
    cd "$LOCAL_DIR"
fi

echo "[2/4] 安装依赖..."
pip install -q flask werkzeug requests jieba duckduckgo-search lxml

echo "[3/4] 启动服务..."
echo ""
echo "========================================"
echo "  服务启动成功！"
echo "========================================"
echo ""

python -m src.app
