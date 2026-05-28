"""数据库操作"""

import os
from pathlib import Path
from sqlmodel import SQLModel, create_engine, Session

from .models import OperationRecord, CommitSummary


def get_db_path() -> Path:
    """获取数据库路径"""
    db_dir = Path("/Users/zhenqi/demo/ai-contributions")
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "contributions.db"


def get_snapshots_path() -> Path:
    """获取快照存储路径"""
    base = Path("/Users/zhenqi/demo/ai-contributions/snapshots")
    base.mkdir(parents=True, exist_ok=True)
    return base


def create_db():
    """创建数据库和表"""
    db_path = get_db_path()
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    SQLModel.metadata.create_all(engine)
    print(f"Database created: {db_path}")
    return engine


def get_engine():
    """获取数据库引擎"""
    db_path = get_db_path()
    return create_engine(f"sqlite:///{db_path}", echo=False)


def save_operation(record: OperationRecord) -> int:
    """保存操作记录"""
    engine = get_engine()
    with Session(engine) as session:
        # 检查是否已存在
        existing = session.exec(
            OperationRecord.where(OperationRecord.operation_id == record.operation_id)
        ).first()
        if existing:
            return existing.id

        session.add(record)
        session.commit()
        session.refresh(record)
    return record.id


def save_snapshot(file_content: bytes, operation_id: str, file_path: str) -> str:
    """保存文件快照，返回路径"""
    snap_dir = get_snapshots_path()
    snap_path = snap_dir / f"{operation_id}_{Path(file_path).name}"
    snap_path.write_bytes(file_content)
    return str(snap_path)


def get_operations(
    project_name: str = None,
    author_name: str = None,
    session_id: str = None,
    from_date: str = None,
    to_date: str = None,
    limit: int = 1000,
) -> list:
    """查询操作记录"""
    from sqlmodel import select

    engine = get_engine()
    with Session(engine) as session:
        statement = select(OperationRecord)

        if project_name:
            statement = statement.where(OperationRecord.project_name == project_name)
        if author_name:
            statement = statement.where(OperationRecord.author_name == author_name)
        if session_id:
            statement = statement.where(OperationRecord.session_id == session_id)
        if from_date:
            statement = statement.where(OperationRecord.timestamp >= from_date)
        if to_date:
            statement = statement.where(OperationRecord.timestamp <= to_date)

        statement = statement.order_by(OperationRecord.timestamp.desc())
        statement = statement.limit(limit)

        results = session.exec(statement)
        return [r.model_dump() for r in results]


def save_commit_summary(summary: CommitSummary) -> int:
    """保存提交汇总"""
    engine = get_engine()
    with Session(engine) as session:
        existing = session.exec(
            CommitSummary.where(CommitSummary.commit_hash == summary.commit_hash)
        ).first()
        if existing:
            # 更新
            for key, value in summary.model_dump().items():
                setattr(existing, key, value)
            session.add(existing)
        else:
            session.add(summary)
        session.commit()
    return summary.id or 0


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
        base_query = select(OperationRecord)
        if project_name:
            base_query = base_query.where(OperationRecord.project_name == project_name)
        if author_name:
            base_query = base_query.where(OperationRecord.author_name == author_name)
        if from_date:
            base_query = base_query.where(OperationRecord.timestamp >= from_date)
        if to_date:
            base_query = base_query.where(OperationRecord.timestamp <= to_date)

        records = session.exec(base_query).all()

        if not records:
            return {
                "total_operations": 0,
                "total_files": 0,
                "total_lines_added": 0,
                "total_lines_removed": 0,
            }

        import json
        total_added = 0
        total_removed = 0
        files = set()

        for r in records:
            files.add(r.file_path)
            try:
                added = json.loads(r.diff_added) if r.diff_added else []
                removed = json.loads(r.diff_removed) if r.diff_removed else []
                total_added += len(added)
                total_removed += len(removed)
            except:
                pass

        return {
            "total_operations": len(records),
            "total_files": len(files),
            "total_lines_added": total_added,
            "total_lines_removed": total_removed,
        }
