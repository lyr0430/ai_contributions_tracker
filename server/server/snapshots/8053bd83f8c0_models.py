"""数据库模型"""

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class AnalysisRecord(SQLModel, table=True):
    """单次分析记录"""
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

    # 分析时间
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)

    # 核心指标
    total_push_lines: int = 0
    ai_events_count: int = 0
    generation_rate: float = 0.0  # AI 生成率
    retention_rate: float = 0.0   # AI 存活率
    net_contribution: float = 0.0 # AI 净贡献

    # 明细统计
    ai_pure_lines: int = 0        # 纯 AI
    ai_modified_lines: int = 0    # AI 修改
    mixed_lines: int = 0          # 混合
    human_lines: int = 0          # 人工
    deleted_ai_lines: int = 0     # 已删除 AI

    # 文件详情 (JSON)
    files_json: str = ""          # 每文件详情


class SessionRecord(SQLModel, table=True):
    """Session 记录"""
    id: Optional[int] = Field(default=None, primary_key=True)

    session_id: str = Field(index=True, unique=True)
    project_name: str = Field(index=True)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None

    # 统计
    total_events: int = 0
    total_lines_edited: int = 0
