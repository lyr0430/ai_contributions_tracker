"""数据库模型"""

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class OperationRecord(SQLModel, table=True):
    """提交记录（pre-push 批量推送）"""
    id: Optional[int] = Field(default=None, primary_key=True)

    # 项目信息
    project_name: str = Field(index=True)
    project_path: str

    # 提交信息
    commit_hash: str = Field(index=True)
    branch_name: str
    author_name: str = Field(index=True)
    author_email: str = Field(index=True)
    commit_time: datetime

    # 文件变更
    file_path: str = Field(index=True)

    # 来源：ai (Claude Code 修改过) | human (纯手动)
    source: str = Field(default="human")

    # AI 归属分析
    ai_pure_lines: int = 0
    ai_modified_lines: int = 0
    mixed_lines: int = 0
    human_lines: int = 0
    total_lines: int = 0

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
