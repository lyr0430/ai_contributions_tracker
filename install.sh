#!/bin/bash

# AI Code Contributions 一键安装脚本
#
# 用法 1（从 clone 的仓库执行）：
#   cd your-project && bash /path/to/ai-code-contributions/install.sh
#
# 用法 2（一行命令，自动下载）：
#   cd your-project && bash <(curl -sL https://raw.githubusercontent.com/lyr0430/ai_contributions_tracker/main/install.sh)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(pwd)"
REPO_ZIP_URL="https://github.com/lyr0430/ai_contributions_tracker/archive/refs/heads/main.zip"
CLONE_DIR="/tmp/ai-contributions-tracker-$$"

echo "========================================="
echo "  AI Contribution Tracker 安装"
echo "========================================="
echo ""

# 检查是否在 git 仓库中
if [ ! -d ".git" ]; then
    echo "错误: 当前目录不是 git 仓库"
    echo "请先进入你的项目目录再执行此脚本"
    exit 1
fi

echo "项目目录: $PROJECT_DIR"
echo ""

# 检查 Python
PYTHON=""
for cmd in /Library/Frameworks/Python.framework/Versions/*/bin/python3 /usr/local/bin/python3 python3 python; do
    if [ -x "$cmd" ] 2>/dev/null || command -v "$cmd" &> /dev/null; then
        version=$("$cmd" --version 2>&1)
        if echo "$version" | grep -q "Python 3"; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "错误: 未找到 Python 3"
    exit 1
fi

echo "Python:    $($PYTHON --version)"

# 如果是从 curl 执行的（没有 tracker 源码），自动下载
SOURCE_TRACKER="$SCRIPT_DIR/tracker/ai_tracker"
if [ ! -f "$SOURCE_TRACKER/__init__.py" ]; then
    echo ""
    echo "下载 ai-tracker..."
    rm -rf "$CLONE_DIR"
    mkdir -p "$CLONE_DIR"

    ZIP_FILE="$CLONE_DIR/repo.zip"
    if curl -sL "$REPO_ZIP_URL" -o "$ZIP_FILE" && [ -s "$ZIP_FILE" ]; then
        unzip -q "$ZIP_FILE" -d "$CLONE_DIR"
        # 解压后的目录名是 ai_contributions_tracker-main
        SOURCE_TRACKER="$CLONE_DIR/ai_contributions_tracker-main/tracker/ai_tracker"
    else
        echo "下载失败，请检查网络连接"
        rm -rf "$CLONE_DIR"
        exit 1
    fi
fi

if [ ! -f "$SOURCE_TRACKER/__init__.py" ]; then
    echo "错误: 下载的文件不完整，请重试"
    rm -rf "$CLONE_DIR"
    exit 1
fi

# 复制 ai_tracker 到项目的 .ai-contributions/ 目录（无需 pip install）
LOCAL_TRACKER=".ai-contributions/ai_tracker"

echo ""
echo "复制 ai_tracker 到 $LOCAL_TRACKER ..."
mkdir -p ".ai-contributions"
rm -rf "$LOCAL_TRACKER"
cp -r "$SOURCE_TRACKER" "$LOCAL_TRACKER"
# 复制 .env 配置文件（从 tracker 源码的父目录）
TRACKER_PARENT="$(dirname "$SOURCE_TRACKER")"
if [ -f "$TRACKER_PARENT/.env" ]; then
    cp "$TRACKER_PARENT/.env" ".ai-contributions/.env"
fi
echo "  已复制 ai_tracker 到 $LOCAL_TRACKER"

# 清理临时文件
rm -rf "$CLONE_DIR"

# 读取 server 地址
SERVER_URL=$($PYTHON -c "
import sys
sys.path.insert(0, '$LOCAL_TRACKER')
from ai_tracker.config import DEFAULT_SERVER_URL
print(DEFAULT_SERVER_URL)
" 2>/dev/null || echo "http://localhost:8000")

echo "Server:    $SERVER_URL"
echo ""

# 执行安装（写入 git hook + claude hook）
PYTHONPATH="$LOCAL_TRACKER:$PYTHONPATH" $PYTHON -m ai_tracker install

echo ""
echo "========================================="
echo "  安装完成！以后 git push 自动上报。"
echo "========================================="
