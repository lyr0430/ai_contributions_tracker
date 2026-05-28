"""
一键安装 Git hooks 和 Claude Code hooks。
跨平台兼容：Windows（PowerShell/cmd）+ macOS/Linux（bash/zsh）。
"""

import json
import os
import stat
import sys
from pathlib import Path
from typing import Optional

from .config import find_repo_root


def install_all(repo_root: Path = None, python_path: str = None, server_url: str = None) -> None:
    """安装所有 hooks（零配置：不传 server 时自动使用默认地址）"""
    from .config import DEFAULT_SERVER_URL

    root = repo_root or find_repo_root()
    py = python_path or _detect_python()
    server_url = server_url or DEFAULT_SERVER_URL

    print(f"Repo root: {root}")
    print(f"Python:    {py}")
    print(f"Server:    {server_url}")
    print()

    _install_git_hook(root, py, server_url)
    _install_claude_hook(root, py, server_url)
    _update_gitignore(root)

    print()
    print("All hooks installed. AI contribution tracking is active.")


def _detect_python() -> str:
    """检测可用的 Python 命令"""
    # 优先 python3，其次 python
    for cmd in ["python3", "python"]:
        try:
            import subprocess
            r = subprocess.run(
                [cmd, "--version"],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode == 0 and "Python 3" in r.stdout:
                return cmd
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue

    # Windows 上可能需要完整路径
    return sys.executable


# ── Git Pre-Push Hook ───────────────────────────────────

def _install_git_hook(repo_root: Path, python_cmd: str, server_url: str = None) -> None:
    """安装 git pre-push hook"""
    hooks_dir = repo_root / ".git" / "hooks"
    hooks_dir.mkdir(exist_ok=True)

    hook_path = hooks_dir / "pre-push"
    hook_content = _generate_hook_script(python_cmd, repo_root, server_url)

    # 如果已存在，备份
    if hook_path.exists():
        backup = hook_path.with_suffix(".bak")
        hook_path.rename(backup)
        print(f"  Backed up existing hook to {backup}")

    hook_path.write_text(hook_content, encoding="utf-8")

    # Unix: 设置可执行权限
    if sys.platform != "win32":
        hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    print(f"  Installed git pre-push hook: {hook_path}")


def _generate_hook_script(python_cmd: str, repo_root: Path, server_url: str = None) -> str:
    """生成 pre-push hook 脚本（跨平台）"""

    # 本地安装路径：.ai-contributions/ai_tracker/
    local_tracker = repo_root / ".ai-contributions" / "ai_tracker"
    local_tracker_escaped = str(local_tracker).replace("\\", "\\\\")

    server_arg = f'--push "{server_url}"'
    project_arg = f'--project "{repo_root.name}"'

    if sys.platform == "win32":
        # Windows: 使用 Python 包装脚本
        server_arg = f'server_url="{server_url}"'
        project_arg = f'project_name="{repo_root.name}"'
        args = ', '.join([server_arg, project_arg])
        return f'''#!/usr/bin/env python3
"""Git pre-push hook — AI Contribution Tracker"""
import sys
sys.path.insert(0, r"{local_tracker}")
try:
    from ai_tracker.__main__ import run_pre_push_analysis
    run_pre_push_analysis({args})
except Exception as e:
    print(f"[ai-tracker] Analysis error: {{e}}", file=sys.stderr)
'''
    else:
        # macOS / Linux: 使用本地 .ai-contributions/ai_tracker/
        return f'''#!/bin/sh
# AI Contribution Tracker — pre-push hook
PYTHON="{python_cmd}"
export PYTHONPATH="{local_tracker_escaped}:$PYTHONPATH"
"$PYTHON" -m ai_tracker pre-push {server_arg} {project_arg}
RET=$?
if [ $RET -ne 0 ]; then
    echo "[ai-tracker] Hook exited with code $RET (non-blocking)"
fi
exit 0
'''


# ── Claude Code Hooks ───────────────────────────────────

def _install_claude_hook(repo_root: Path, python_cmd: str, server_url: str = None) -> None:
    """安装 Claude Code hooks（配置 .claude/settings.json）"""
    claude_dir = repo_root / ".claude"
    claude_dir.mkdir(exist_ok=True)
    settings_path = claude_dir / "settings.json"

    # 读取现有配置
    settings = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            settings = {}

    # 使用本地 .ai-contributions/ai_tracker/，无需 pip install
    local_tracker = repo_root / ".ai-contributions" / "ai_tracker"
    env_vars = f'AI_TRACKER_SERVER="{server_url}" AI_TRACKER_PROJECT="{repo_root.name}" PYTHONPATH="{local_tracker}" '

    if sys.platform == "win32":
        hook_cmd = f'{python_cmd} -c "import sys,os; sys.path.insert(0, r\'{local_tracker}\'); os.environ[\"AI_TRACKER_SERVER\"]=\"{server_url}\"; from ai_tracker.hook_handler import handle_hook; handle_hook()"'
    else:
        hook_cmd = f'{env_vars}{python_cmd} -m ai_tracker.hook_handler'

    # 配置 hooks
    if "hooks" not in settings:
        settings["hooks"] = {}

    hook_entry = {
        "matcher": "Write|Edit|MultiEdit",
        "hooks": [
            {
                "type": "command",
                "command": hook_cmd,
            }
        ],
    }

    # PostToolUse hooks
    post_hooks = settings["hooks"].get("PostToolUse", [])

    # 移除旧的 ai-tracker hooks（通过 command 关键字判断）
    post_hooks = [
        h for h in post_hooks
        if not any(
            "ai_tracker" in hook.get("command", "")
            for hook in h.get("hooks", [])
        )
    ]
    post_hooks.append(hook_entry)
    settings["hooks"]["PostToolUse"] = post_hooks

    # 写入配置
    settings_path.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"  Updated Claude Code hooks: {settings_path}")


# ── .gitignore 更新 ─────────────────────────────────────

def _update_gitignore(repo_root: Path) -> None:
    """确保 .ai-contributions/ 在 .gitignore 中"""
    gitignore = repo_root / ".gitignore"
    entry = ".ai-contributions/"

    content = ""
    if gitignore.exists():
        content = gitignore.read_text(encoding="utf-8")

    if entry not in content:
        marker = "# AI Contribution Tracker (auto-generated)"
        block = f"\n{marker}\n{entry}\n"

        with open(gitignore, "a", encoding="utf-8") as f:
            f.write(block)

        print(f"  Added '{entry}' to .gitignore")
    else:
        print(f"  '{entry}' already in .gitignore")
