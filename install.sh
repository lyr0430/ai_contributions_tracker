#!/bin/bash

# AI Code Contributions 一键安装脚本
# 用法：在你的项目目录下执行
#   bash /path/to/ai-code-contributions/install.sh
#
# 或者远程安装（替换为实际 GitLab 地址）：
#   bash <(curl -s https://gitlab.com/your-org/ai-code-contributions/-/raw/main/install.sh)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(pwd)"

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

# 检查 Python（优先非 Homebrew 的 Python，避免 externally-managed-environment）
PYTHON=""
# 先找非 Homebrew 的 Python
for cmd in /Library/Frameworks/Python.framework/Versions/*/bin/python3 /usr/local/bin/python3; do
    if [ -x "$cmd" ]; then
        version=$("$cmd" --version 2>&1)
        if echo "$version" | grep -q "Python 3"; then
            PYTHON="$cmd"
            break
        fi
    fi
done
# 再找通用的
if [ -z "$PYTHON" ]; then
    for cmd in python3 python; do
        if command -v "$cmd" &> /dev/null; then
            version=$("$cmd" --version 2>&1)
            if echo "$version" | grep -q "Python 3"; then
                PYTHON="$cmd"
                break
            fi
        fi
    done
fi

if [ -z "$PYTHON" ]; then
    echo "错误: 未找到 Python 3"
    exit 1
fi

echo "Python:    $($PYTHON --version)"

# 安装 ai-tracker 包（如果尚未安装）
if ! $PYTHON -c "import ai_tracker" 2>/dev/null; then
    echo ""
    echo "安装 ai-tracker 包..."
    # 依次尝试：editable --user → editable → --user → 普通 → --break-system-packages
    $PYTHON -m pip install --user -e "$SCRIPT_DIR/tracker" --quiet 2>/dev/null \
        || $PYTHON -m pip install -e "$SCRIPT_DIR/tracker" --quiet 2>/dev/null \
        || $PYTHON -m pip install --user "$SCRIPT_DIR/tracker" --quiet 2>/dev/null \
        || $PYTHON -m pip install "$SCRIPT_DIR/tracker" --quiet 2>/dev/null \
        || $PYTHON -m pip install --user --break-system-packages "$SCRIPT_DIR/tracker" --quiet 2>/dev/null \
        || $PYTHON -m pip install --break-system-packages "$SCRIPT_DIR/tracker" --quiet
fi

echo "Server:    $($PYTHON -c "from ai_tracker.config import DEFAULT_SERVER_URL; print(DEFAULT_SERVER_URL)")"
echo ""

# 执行安装（写入 git hook + claude hook）
$PYTHON -m ai_tracker install

echo ""
echo "========================================="
echo "  安装完成！以后 git push 自动上报。"
echo "========================================="
