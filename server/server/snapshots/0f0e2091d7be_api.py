"""FastAPI 应用"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import json

from .db import (
    save_operation, save_snapshot, save_commit_summary,
    get_operations, get_summary, create_db
)
from .models import OperationRecord, CommitSummary


app = FastAPI(title="AI Contributions Server")


class OperationRequest(BaseModel):
    """操作记录请求"""
    project_name: str
    project_path: str
    session_id: str
    operation_id: str
    timestamp: datetime
    operation: str
    file_path: str
    diff_added: List[str]
    diff_removed: List[str]
    snapshot_content: Optional[str] = None  # Base64 或原始内容
    file_hash: str
    commit_hash: Optional[str] = None
    branch_name: Optional[str] = None
    author_name: Optional[str] = None
    author_email: Optional[str] = None


class CommitSummaryRequest(BaseModel):
    """提交汇总请求"""
    project_name: str
    project_path: str
    commit_hash: str
    branch_name: str
    author_name: str
    author_email: str
    commit_time: datetime

    # 统计
    total_operations: int
    total_files_changed: int
    total_lines_added: int
    total_lines_removed: int

    # AI 分析
    ai_pure_lines: int
    ai_modified_lines: int
    mixed_lines: int
    human_lines: int


@app.on_event("startup")
async def startup():
    """启动时创建数据库"""
    create_db()


@app.post("/api/operation")
async def save_operation_endpoint(req: OperationRequest):
    """保存单次操作记录"""
    # 保存快照
    snapshot_path = ""
    if req.snapshot_content:
        snapshot_path = save_snapshot(
            req.snapshot_content.encode("utf-8"),
            req.operation_id,
            req.file_path,
        )

    record = OperationRecord(
        project_name=req.project_name,
        project_path=req.project_path,
        session_id=req.session_id,
        operation_id=req.operation_id,
        timestamp=req.timestamp,
        operation=req.operation,
        file_path=req.file_path,
        diff_added=json.dumps(req.diff_added),
        diff_removed=json.dumps(req.diff_removed),
        snapshot_path=snapshot_path,
        file_hash=req.file_hash,
        commit_hash=req.commit_hash or "",
        branch_name=req.branch_name or "",
        author_name=req.author_name or "",
        author_email=req.author_email or "",
    )

    record_id = save_operation(record)
    return {"id": record_id, "status": "saved"}


@app.post("/api/commit")
async def save_commit_endpoint(req: CommitSummaryRequest):
    """保存提交汇总"""
    summary = CommitSummary(
        project_name=req.project_name,
        project_path=req.project_path,
        commit_hash=req.commit_hash,
        branch_name=req.branch_name,
        author_name=req.author_name,
        author_email=req.author_email,
        commit_time=req.commit_time,
        total_operations=req.total_operations,
        total_files_changed=req.total_files_changed,
        total_lines_added=req.total_lines_added,
        total_lines_removed=req.total_lines_removed,
        ai_pure_lines=req.ai_pure_lines,
        ai_modified_lines=req.ai_modified_lines,
        mixed_lines=req.mixed_lines,
        human_lines=req.human_lines,
    )

    commit_id = save_commit_summary(summary)
    return {"id": commit_id, "status": "saved"}


@app.get("/api/operations")
async def list_operations(
    project_name: Optional[str] = None,
    author_name: Optional[str] = None,
    session_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 1000,
):
    """查询操作记录"""
    results = get_operations(
        project_name=project_name,
        author_name=author_name,
        session_id=session_id,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
    )
    return {"data": results, "total": len(results)}


@app.get("/api/summary")
async def get_summary_endpoint(
    project_name: Optional[str] = None,
    author_name: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
):
    """获取汇总统计"""
    summary = get_summary(
        project_name=project_name,
        author_name=author_name,
        from_date=from_date,
        to_date=to_date,
    )
    return summary


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
