"""所有数据结构定义，纯 Python dataclass，零外部依赖"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class LineDiff:
    """单次操作中的行级变更"""
    added: Dict[int, str] = field(default_factory=dict)    # {行号：内容}
    removed: Dict[int, str] = field(default_factory=dict)


@dataclass
class Event:
    """一条 Claude Code 操作事件（不可变记录）"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    session_id: str = ""
    operation: str = ""           # "write" | "edit" | "multi_edit"
    file_path: str = ""           # 相对于 repo root 的路径，统一用 /
    diff: LineDiff = field(default_factory=LineDiff)
    snapshot_path: str = ""       # 操作后完整文件快照的路径
    file_hash_after: str = ""     # 操作后文件的 sha256

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "operation": self.operation,
            "file_path": self.file_path,
            "diff": {
                "added": {str(k): v for k, v in self.diff.added.items()},
                "removed": {str(k): v for k, v in self.diff.removed.items()},
            },
            "snapshot_path": self.snapshot_path,
            "file_hash_after": self.file_hash_after,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Event:
        diff_raw = d.get("diff", {})
        return cls(
            id=d["id"],
            timestamp=d["timestamp"],
            session_id=d.get("session_id", ""),
            operation=d["operation"],
            file_path=d["file_path"],
            diff=LineDiff(
                added={int(k): v for k, v in diff_raw.get("added", {}).items()},
                removed={int(k): v for k, v in diff_raw.get("removed", {}).items()},
            ),
            snapshot_path=d.get("snapshot_path", ""),
            file_hash_after=d.get("file_hash_after", ""),
        )


@dataclass
class LineAttribution:
    """最终版本中一行的归因结果"""
    line_number: int
    content: str
    source: str                     # "ai_pure" | "ai_modified" | "human" | "mixed"
    ai_ratio: float = 0.0           # 0.0 ~ 1.0
    matched_event_id: Optional[str] = None
    similarity_score: float = 0.0


@dataclass
class FileAttribution:
    """单个文件的归因结果"""
    file_path: str
    total_lines: int = 0
    ai_pure_lines: int = 0
    ai_modified_lines: int = 0
    human_lines: int = 0
    mixed_lines: int = 0
    ai_weighted_sum: float = 0.0    # 加权 AI 贡献总和
    line_details: List[LineAttribution] = field(default_factory=list)

    @property
    def ai_contribution_ratio(self) -> float:
        if self.total_lines == 0:
            return 0.0
        return self.ai_weighted_sum / self.total_lines


@dataclass
class DeletedAIContribution:
    """AI 生成但最终被删除的代码"""
    file_path: str
    content: str
    event_id: str


@dataclass
class AnalysisResult:
    """完整分析结果"""
    files: List[FileAttribution] = field(default_factory=list)
    deleted_ai: List[DeletedAIContribution] = field(default_factory=list)
    ai_events_count: int = 0
    total_push_lines: int = 0
    ai_events_total_lines: int = 0    # AI 事件中涉及的总行数

    @property
    def ai_pure_total(self) -> int:
        return sum(f.ai_pure_lines for f in self.files)

    @property
    def ai_modified_total(self) -> int:
        return sum(f.ai_modified_lines for f in self.files)

    @property
    def human_total(self) -> int:
        return sum(f.human_lines for f in self.files)

    @property
    def mixed_total(self) -> int:
        return sum(f.mixed_lines for f in self.files)

    @property
    def deleted_ai_total(self) -> int:
        return len(self.deleted_ai)

    @property
    def generation_rate(self) -> float:
        """AI 生成率：AI 写的行 / 总行数"""
        if self.total_push_lines == 0:
            return 0.0
        ai_generated = self.ai_pure_total + self.ai_modified_total + self.mixed_total
        return ai_generated / max(self.total_push_lines, 1)

    @property
    def retention_rate(self) -> float:
        """AI 存活率：AI 写的留在 push 中的 / AI 写的总数"""
        retained = self.ai_pure_total + self.ai_modified_total + self.mixed_total * 0.5
        total_generated = retained + self.deleted_ai_total
        if total_generated == 0:
            return 0.0
        return retained / total_generated

    @property
    def net_contribution(self) -> float:
        """AI 净贡献率：最终 push 中可归因于 AI 的行 / 总行数"""
        if self.total_push_lines == 0:
            return 0.0
        weighted = sum(f.ai_weighted_sum for f in self.files)
        return weighted / self.total_push_lines
