"""事件的存储和读取，使用 JSONL 格式实现追加写入和高效读取"""

import hashlib
import json
from pathlib import Path
from typing import List, Optional

from . import config
from .models import Event, LineDiff


def _compute_file_hash(file_path: Path) -> str:
    """计算文件 SHA256"""
    if not file_path.exists():
        return ""
    h = hashlib.sha256()
    h.update(file_path.read_bytes())
    return h.hexdigest()


def _normalize_rel_path(file_path: str, repo_root: Path) -> str:
    """将绝对路径转换为相对于 repo root 的路径，统一用 / 分隔"""
    p = Path(file_path)
    if p.is_absolute():
        try:
            return str(p.resolve().relative_to(repo_root.resolve())).replace("\\", "/")
        except ValueError:
            return str(p).replace("\\", "/")
    return str(p).replace("\\", "/")


def save_event(event: Event, repo_root: Path) -> None:
    """追加一条事件到 events.jsonl"""
    events_file = config.EVENTS_FILE or (repo_root / ".ai-contributions" / "events.jsonl")
    events_file.parent.mkdir(parents=True, exist_ok=True)

    with open(events_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")


def load_events(repo_root: Path = None, file_filter: Optional[str] = None) -> List[Event]:
    """读取所有事件，可按文件路径过滤"""
    from .config import init_paths
    if repo_root:
        init_paths(repo_root)
        from . import config as cfg
        events_file = cfg.EVENTS_FILE
    else:
        from . import config as cfg
        events_file = cfg.EVENTS_FILE

    if not events_file or not events_file.exists():
        return []

    events = []
    with open(events_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                evt = Event.from_dict(d)
                if file_filter and evt.file_path != file_filter:
                    continue
                events.append(evt)
            except (json.JSONDecodeError, KeyError):
                continue  # 跳过损坏的行

    return events


def save_snapshot(file_path: Path, event_id: str, repo_root: Path = None) -> str:
    """保存文件快照到项目根目录 .ai-contributions/snapshots/"""
    if repo_root:
        snap_dir = repo_root / ".ai-contributions" / "snapshots"
    elif config.CONTRIB_DIR:
        snap_dir = config.CONTRIB_DIR / "snapshots"
    else:
        # 回退到当前工作目录
        snap_dir = Path.cwd() / ".ai-contributions" / "snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    snap_name = f"{event_id}_{file_path.name}"
    snap_path = snap_dir / snap_name
    snap_path.write_bytes(file_path.read_bytes())
    return str(snap_path)


def load_snapshot(snapshot_path: str) -> Optional[List[str]]:
    """加载快照文件内容，返回行列表"""
    p = Path(snapshot_path)
    if not p.exists():
        return None
    try:
        content = p.read_text(encoding="utf-8")
        return content.splitlines()
    except (UnicodeDecodeError, OSError):
        return None
