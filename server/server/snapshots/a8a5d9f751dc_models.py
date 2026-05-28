"""数据库模型"""

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class OperationRecord(SQLModel, table=True):
    """单次操作记录（AI + 手动）"""
    id: Optional[int] = Field(default=None, primary_key=True)

    # 项目信息
    project_name: str = Field(index=True)
    project_path: str

    # Session 信息
    session_id: str = Field(index=True)

    # 操作信息
    operation_id: str = Field(unique=True, index=True)
    timestamp: datetime
    operation: str  # write | edit | multi_edit | push_file
    file_path: str = Field(index=True)

    # Diff 内容
    diff_added: str = ""  # JSON 数组
    diff_removed: str = ""  # JSON 数组

    # 快照
    snapshot_path: str = ""
    file_hash: str = ""

    # 提交时补充
    commit_hash: str = ""
    branch_name: str = ""
    author_name: str = Field(index=True)
    author_email: str = Field(index=True)

    # 来源：ai (Claude Code 实时记录) | push_analysis (pre-push 批量分析)
    source: str = Field(default="ai")

    # AI 归属分析（source=push_analysis 时填充）
    ai_pure_lines: int = 0
    ai_modified_lines: int = 0
    mixed_lines: int = 0
    human_lines: int = 0

    # 服务器记录时间
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CommitSummary(SQLModel, table=True):
    """提交汇总（用于快速查询）"""
    id: Optional[int] = Field(default=None, primary_key=True)

    # 项目信息
    project_name: str = Field(index=True)
    project_path: str

    # 提交信息
    commit_hash: str = Field(unique=True, index=True)
    branch_name: str
    author_name: str = Field(index=True)
    author_email: str = Field(index=True)
    commit_time: datetime

    # 统计
    total_operations: int = 0
    total_files_changed: int = 0
    total_lines_added: int = 0
    total_lines_removed: int = 0

    # AI 分析结果
    ai_pure_lines: int = 0
    ai_modified_lines: int = 0
    mixed_lines: int = 0
    human_lines: int = 0

    created_at: datetime = Field(default_factory=datetime.utcnow)
