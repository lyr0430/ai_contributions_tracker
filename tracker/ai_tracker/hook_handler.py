"""
Claude Code Hooks 的入口脚本。
Claude Code 在每次 Tool 调用后通过 stdin 传入 JSON，
本脚本解析 Write / Edit / MultiEdit 操作并记录事件。

用法（在 .claude/settings.json 中配置）：
  python -m ai_tracker.hook_handler

环境变量:
  AI_TRACKER_SERVER - 服务器 URL (可选)
  AI_TRACKER_PROJECT - 项目名称 (可选)
"""

import hashlib
import json
import sys
import os
from pathlib import Path

from .models import Event, LineDiff
from .event_store import save_event, save_snapshot, _normalize_rel_path, _compute_file_hash
from .config import find_repo_root, SESSION_ID


def parse_edit_input(tool_input: dict, repo_root: Path) -> Event:
    """解析 Edit / Write 工具的输入，生成 Event"""
    file_path_raw = tool_input.get("file_path", "")
    rel_path = _normalize_rel_path(file_path_raw, repo_root)
    abs_path = repo_root / rel_path

    diff = LineDiff()
    operation = "write"

    if "content" in tool_input:
        # Write 操作：写入整个文件
        operation = "write"
        content = tool_input["content"]
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            diff.added[i] = line
        # removed 在 Write 场景下不太有意义，因为是全量覆盖
        # 如果需要精确的 removed，需要保存操作前的快照（PreToolUse）

    elif "old_string" in tool_input and "new_string" in tool_input:
        # 单次 Edit
        operation = "edit"
        old_str = tool_input["old_string"]
        new_str = tool_input["new_string"]
        # 我们记录 old/new 内容，精确行号需要读取当前文件
        _compute_line_numbers(abs_path, old_str, new_str, diff)

    elif "edits" in tool_input:
        # MultiEdit
        operation = "multi_edit"
        for edit_item in tool_input["edits"]:
            old_str = edit_item.get("old_string", "")
            new_str = edit_item.get("new_string", "")
            _compute_line_numbers(abs_path, old_str, new_str, diff)

    # 保存快照
    snapshot_path = ""
    file_hash = ""
    if abs_path.exists():
        event_id_tmp = hashlib.md5(
            f"{rel_path}:{Path(file_path_raw).stat().st_mtime if Path(file_path_raw).exists() else 0}".encode()
        ).hexdigest()[:12]
        snapshot_path = save_snapshot(abs_path, event_id_tmp)
        file_hash = _compute_file_hash(abs_path)

    event = Event(
        session_id=SESSION_ID,
        operation=operation,
        file_path=rel_path,
        diff=diff,
        snapshot_path=snapshot_path,
        file_hash_after=file_hash,
    )

    # 如果快照路径已生成，用真正的 event_id 重命名
    if snapshot_path:
        snap_dir = Path(snapshot_path).parent
        old_snap = Path(snapshot_path)
        new_snap = snap_dir / f"{event.id}_{abs_path.name}"
        if old_snap.exists() and old_snap != new_snap:
            old_snap.rename(new_snap)
            event.snapshot_path = str(new_snap)

    return event


def _compute_line_numbers(
    file_path: Path, old_str: str, new_str: str, diff: LineDiff
) -> None:
    """
    读取文件内容，找到 old_str 的位置，记录被替换的行号。
    如果文件不存在（新建），new_str 的每一行都算 added。
    """
    if not file_path.exists():
        for i, line in enumerate(new_str.splitlines(), 1):
            diff.added[i] = line
        return

    try:
        content = file_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return

    lines = content.splitlines()

    # 在文件中查找 old_str 的位置
    old_lines = old_str.splitlines()
    if not old_lines:
        # 没有 old_string，可能是新增
        for i, line in enumerate(new_str.splitlines(), 1):
            diff.added[len(lines) + i] = line
        return

    # 逐行搜索 old_str 的起始行
    start_idx = None
    for i, line in enumerate(lines):
        if line.strip() == old_lines[0].strip():
            # 检查后续行是否也匹配
            match = True
            for j, old_line in enumerate(old_lines):
                if i + j >= len(lines) or lines[i + j].strip() != old_line.strip():
                    match = False
                    break
            if match:
                start_idx = i
                break

    if start_idx is None:
        # 没找到精确匹配，把 new_str 当作追加
        for i, line in enumerate(new_str.splitlines(), 1):
            diff.added[len(lines) + i] = line
        return

    # 记录被删除的行
    for j, old_line in enumerate(old_lines):
        diff.removed[start_idx + j + 1] = old_line  # 1-indexed

    # 记录新增的行
    new_lines = new_str.splitlines()
    for j, new_line in enumerate(new_lines):
        diff.added[start_idx + j + 1] = new_line  # 1-indexed


def _push_operation_to_server(event: Event, repo_root: Path):
    """推送操作记录到服务器"""
    from .config import DEFAULT_SERVER_URL
    server_url = os.environ.get("AI_TRACKER_SERVER") or DEFAULT_SERVER_URL

    project_name = os.environ.get("AI_TRACKER_PROJECT", repo_root.name)

    # 读取快照内容
    snapshot_content = ""
    if event.snapshot_path and Path(event.snapshot_path).exists():
        try:
            snapshot_content = Path(event.snapshot_path).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as e:
            print(f"[ai-tracker] Failed to read snapshot: {e}", file=sys.stderr)

    payload = {
        "project_name": project_name,
        "project_path": str(repo_root),
        "session_id": event.session_id or "",
        "operation_id": event.id,
        "timestamp": event.timestamp,
        "operation": event.operation,
        "file_path": event.file_path,
        "diff_added": list(event.diff.added.values()),
        "diff_removed": list(event.diff.removed.values()),
        "snapshot_content": snapshot_content,
        "file_hash": event.file_hash_after,
    }

    try:
        import urllib.request
        req = urllib.request.Request(
            f"{server_url.rstrip('/')}/api/operation",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            print(f"[ai-tracker] Pushed to server: id={data.get('id')}", file=sys.stderr)
    except Exception as e:
        print(f"[ai-tracker] Failed to push to server: {e}", file=sys.stderr)


def handle_hook():
    """主入口：从 stdin 读取 JSON，处理事件"""
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return
        data = json.loads(raw)
    except (json.JSONDecodeError, IOError):
        return

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name not in ("Write", "Edit", "MultiEdit"):
        return

    try:
        repo_root = find_repo_root()
    except RuntimeError:
        print("ai-tracker: not in a git repo, skipping", file=sys.stderr)
        return

    event = parse_edit_input(tool_input, repo_root)
    save_event(event, repo_root)

    # 推送到服务器
    _push_operation_to_server(event, repo_root)

    # 输出给用户（可选，方便调试）
    added_count = len(event.diff.added)
    removed_count = len(event.diff.removed)
    print(
        f"[ai-tracker] Recorded {event.operation} on {event.file_path} "
        f"(+{added_count} -{removed_count})",
        file=sys.stderr,
    )


if __name__ == "__main__":
    handle_hook()
