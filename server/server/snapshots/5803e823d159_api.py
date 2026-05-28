"""FastAPI 应用"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from .db import save_analysis, get_analyses, get_summary, create_db
from .models import AnalysisRecord


app = FastAPI(title="AI Contributions Server")


class AnalysisRequest(BaseModel):
    """分析请求"""
    project_name: str
    project_path: str
    commit_hash: str
    branch_name: str
    author_name: str
    author_email: str
    commit_time: datetime

    # 指标
    total_push_lines: int
    ai_events_count: int
    generation_rate: float
    retention_rate: float
    net_contribution: float

    # 明细
    ai_pure_lines: int
    ai_modified_lines: int
    mixed_lines: int
    human_lines: int
    deleted_ai_lines: int

    # 文件详情
    files: List[dict]


@app.on_event("startup")
async def startup():
    """启动时创建数据库"""
    create_db()


@app.post("/api/analysis")
async def save_analysis_endpoint(req: AnalysisRequest):
    """保存分析结果"""
    import json

    record = AnalysisRecord(
        project_name=req.project_name,
        project_path=req.project_path,
        commit_hash=req.commit_hash,
        branch_name=req.branch_name,
        author_name=req.author_name,
        author_email=req.author_email,
        commit_time=req.commit_time,
        total_push_lines=req.total_push_lines,
        ai_events_count=req.ai_events_count,
        generation_rate=req.generation_rate,
        retention_rate=req.retention_rate,
        net_contribution=req.net_contribution,
        ai_pure_lines=req.ai_pure_lines,
        ai_modified_lines=req.ai_modified_lines,
        mixed_lines=req.mixed_lines,
        human_lines=req.human_lines,
        deleted_ai_lines=req.deleted_ai_lines,
        files_json=json.dumps(req.files),
    )

    record_id = save_analysis(record)
    return {"id": record_id, "status": "saved"}


@app.get("/api/analysis")
async def list_analyses(
    project_name: Optional[str] = None,
    author_name: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 100,
):
    """查询分析记录"""
    results = get_analyses(
        project_name=project_name,
        author_name=author_name,
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
