"""FastAPI 应用"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import json

from .db import (
    save_operation, save_snapshot, save_commit_summary,
    get_operations, get_summary, create_db, get_engine
)
from .models import OperationRecord, CommitSummary
from sqlmodel import Session, select, func


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
    snapshot_content: Optional[str] = None
    file_hash: str
    commit_hash: Optional[str] = None
    branch_name: Optional[str] = None
    author_name: Optional[str] = None
    author_email: Optional[str] = None
    # 来源：ai | push_analysis
    source: str = "ai"
    # AI 归属（push_analysis 时）
    ai_pure_lines: int = 0
    ai_modified_lines: int = 0
    mixed_lines: int = 0
    human_lines: int = 0


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


class AnalysisRequest(BaseModel):
    """pre-push 分析结果请求"""
    project_name: str
    project_path: str
    commit_hash: str
    branch_name: str
    author_name: str
    author_email: str
    commit_time: datetime

    # 统计
    total_push_lines: int
    ai_events_count: int
    generation_rate: float
    retention_rate: float
    net_contribution: float

    # AI 分析
    ai_pure_lines: int
    ai_modified_lines: int
    mixed_lines: int
    human_lines: int
    deleted_ai_lines: int

    # 文件明细（每个文件包含 source 字段区分 AI/手动）
    files: List[dict] = []


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
        source=req.source,
        ai_pure_lines=req.ai_pure_lines,
        ai_modified_lines=req.ai_modified_lines,
        mixed_lines=req.mixed_lines,
        human_lines=req.human_lines,
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


@app.post("/api/analysis")
async def save_analysis_endpoint(req: AnalysisRequest):
    """保存 pre-push 分析结果 - 每个文件一条记录"""
    from .db import save_operation
    from .models import OperationRecord

    record_ids = []
    for f in req.files:
        op_id = f"push_{req.commit_hash[:8]}_{f['path'].replace('/', '_')}"
        total_lines = f.get("ai_pure_lines", 0) + f.get("ai_modified_lines", 0) + f.get("mixed_lines", 0) + f.get("human_lines", 0)
        record = OperationRecord(
            project_name=req.project_name,
            project_path=req.project_path,
            commit_hash=req.commit_hash,
            branch_name=req.branch_name,
            author_name=req.author_name,
            author_email=req.author_email,
            commit_time=req.commit_time,
            file_path=f["path"],
            source=f.get("source", "human"),
            ai_pure_lines=f.get("ai_pure_lines", 0),
            ai_modified_lines=f.get("ai_modified_lines", 0),
            mixed_lines=f.get("mixed_lines", 0),
            human_lines=f.get("human_lines", 0),
            total_lines=total_lines,
        )
        record_ids.append(save_operation(record))

    return {"id": record_ids[0] if record_ids else 0, "status": "saved", "count": len(record_ids)}


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


@app.get("/api/report")
async def get_report(
    project_name: Optional[str] = None,
    author_name: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    group_by: str = "commit",  # commit | file | author
):
    """生成统计报告（从数据库聚合）"""
    from sqlmodel import select, func

    engine = get_engine()
    with Session(engine) as session:
        # 基础查询
        base_query = select(OperationRecord)
        if project_name:
            base_query = base_query.where(OperationRecord.project_name == project_name)
        if author_name:
            base_query = base_query.where(OperationRecord.author_name == author_name)
        if from_date:
            base_query = base_query.where(OperationRecord.commit_time >= from_date)
        if to_date:
            base_query = base_query.where(OperationRecord.commit_time <= to_date)

        records = session.exec(base_query).all()

        # 按 commit 分组
        if group_by == "commit":
            commits = {}
            for r in records:
                key = r.commit_hash or "uncommitted"
                if key not in commits:
                    commits[key] = {
                        "commit_hash": key,
                        "branch_name": r.branch_name,
                        "author_name": r.author_name,
                        "author_email": r.author_email,
                        "commit_time": r.commit_time,
                        "files": [],
                        "ai_pure_lines": 0,
                        "ai_modified_lines": 0,
                        "mixed_lines": 0,
                        "human_lines": 0,
                        "total_lines": 0,
                    }
                commits[key]["files"].append(r.file_path)
                commits[key]["ai_pure_lines"] += r.ai_pure_lines
                commits[key]["ai_modified_lines"] += r.ai_modified_lines
                commits[key]["mixed_lines"] += r.mixed_lines
                commits[key]["human_lines"] += r.human_lines
                commits[key]["total_lines"] += r.total_lines

            total = sum(c["total_lines"] for c in commits.values())
            ai_total = sum(c["ai_pure_lines"] + c["ai_modified_lines"] + c["mixed_lines"] for c in commits.values())

            return {
                "total_commits": len(commits),
                "total_lines": total,
                "ai_lines": ai_total,
                "human_lines": sum(c["human_lines"] for c in commits.values()),
                "ai_percentage": (ai_total / total * 100) if total > 0 else 0,
                "commits": list(commits.values()),
            }

        # 按文件分组
        elif group_by == "file":
            files = {}
            for r in records:
                key = r.file_path
                if key not in files:
                    files[key] = {
                        "file_path": key,
                        "source": r.source,
                        "ai_pure_lines": 0,
                        "ai_modified_lines": 0,
                        "mixed_lines": 0,
                        "human_lines": 0,
                        "total_lines": 0,
                    }
                files[key]["ai_pure_lines"] += r.ai_pure_lines
                files[key]["ai_modified_lines"] += r.ai_modified_lines
                files[key]["mixed_lines"] += r.mixed_lines
                files[key]["human_lines"] += r.human_lines
                files[key]["total_lines"] += r.total_lines

            return {"files": list(files.values())}

        # 按作者分组
        elif group_by == "author":
            authors = {}
            for r in records:
                key = r.author_name
                if key not in authors:
                    authors[key] = {
                        "author_name": key,
                        "author_email": r.author_email,
                        "commits": set(),
                        "files": set(),
                        "ai_pure_lines": 0,
                        "ai_modified_lines": 0,
                        "mixed_lines": 0,
                        "human_lines": 0,
                        "total_lines": 0,
                    }
                authors[key]["commits"].add(r.commit_hash)
                authors[key]["files"].add(r.file_path)
                authors[key]["ai_pure_lines"] += r.ai_pure_lines
                authors[key]["ai_modified_lines"] += r.ai_modified_lines
                authors[key]["mixed_lines"] += r.mixed_lines
                authors[key]["human_lines"] += r.human_lines
                authors[key]["total_lines"] += r.total_lines

            for a in authors.values():
                a["commits"] = len(a["commits"])
                a["files"] = len(a["files"])

            return {"authors": list(authors.values())}

    return {"error": "Invalid group_by parameter"}


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
