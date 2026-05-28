"""数据库操作"""

import os
from pathlib import Path
from sqlmodel import SQLModel, create_engine, Session
from sqlmodel.pool import StaticPool

from .models import AnalysisRecord, SessionRecord


def get_db_path() -> Path:
    """获取数据库路径"""
    db_dir = Path("/Users/zhenqi/demo/ai-contributions")
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "contributions.db"


def create_db():
    """创建数据库和表"""
    db_path = get_db_path()
    engine = create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    print(f"Database created: {db_path}")
    return engine


def get_engine():
    """获取数据库引擎"""
    db_path = get_db_path()
    return create_engine(f"sqlite:///{db_path}", echo=False)


def save_analysis(record: AnalysisRecord):
    """保存分析记录"""
    engine = get_engine()
    with Session(engine) as session:
        session.add(record)
        session.commit()
        session.refresh(record)
    return record.id


def get_analyses(
    project_name: str = None,
    author_name: str = None,
    from_date: str = None,
    to_date: str = None,
    limit: int = 100,
) -> list:
    """查询分析记录"""
    from sqlmodel import select

    engine = get_engine()
    with Session(engine) as session:
        statement = select(AnalysisRecord)

        if project_name:
            statement = statement.where(AnalysisRecord.project_name == project_name)
        if author_name:
            statement = statement.where(AnalysisRecord.author_name == author_name)
        if from_date:
            statement = statement.where(AnalysisRecord.commit_time >= from_date)
        if to_date:
            statement = statement.where(AnalysisRecord.commit_time <= to_date)

        statement = statement.order_by(AnalysisRecord.commit_time.desc())
        statement = statement.limit(limit)

        results = session.exec(statement)
        return [r.model_dump() for r in results]


def get_summary(
    project_name: str = None,
    author_name: str = None,
    from_date: str = None,
    to_date: str = None,
) -> dict:
    """获取汇总统计"""
    from sqlmodel import select, func

    engine = get_engine()
    with Session(engine) as session:
        # 基础查询
        base_query = select(AnalysisRecord)
        if project_name:
            base_query = base_query.where(AnalysisRecord.project_name == project_name)
        if author_name:
            base_query = base_query.where(AnalysisRecord.author_name == author_name)
        if from_date:
            base_query = base_query.where(AnalysisRecord.commit_time >= from_date)
        if to_date:
            base_query = base_query.where(AnalysisRecord.commit_time <= to_date)

        # 执行查询
        records = session.exec(base_query).all()

        if not records:
            return {
                "total_commits": 0,
                "total_lines": 0,
                "avg_ai_contribution": 0.0,
                "ai_pure_total": 0,
                "ai_modified_total": 0,
                "mixed_total": 0,
                "human_total": 0,
            }

        # 计算汇总
        total_lines = sum(r.total_push_lines for r in records)
        total_ai_weighted = sum(r.net_contribution * r.total_push_lines for r in records)

        return {
            "total_commits": len(records),
            "total_lines": total_lines,
            "avg_ai_contribution": total_ai_weighted / max(total_lines, 1),
            "ai_pure_total": sum(r.ai_pure_lines for r in records),
            "ai_modified_total": sum(r.ai_modified_lines for r in records),
            "mixed_total": sum(r.mixed_lines for r in records),
            "human_total": sum(r.human_lines for r in records),
        }
