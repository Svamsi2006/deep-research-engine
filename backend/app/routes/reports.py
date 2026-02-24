"""Reports route — list and retrieve saved reports."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.database import ReportRow, get_session_factory

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/reports")
async def list_reports(limit: int = 20, offset: int = 0):
    """List saved reports, newest first."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = (
            select(ReportRow)
            .order_by(ReportRow.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()

        return [
            {
                "id": r.id,
                "query": r.query,
                "evaluation_score": r.evaluation_score,
                "retry_count": r.retry_count,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "preview": r.report[:200] if r.report else "",
            }
            for r in rows
        ]


@router.get("/api/reports/{report_id}")
async def get_report(report_id: str):
    """Retrieve a single report by ID, including full Markdown and thought trace."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = select(ReportRow).where(ReportRow.id == report_id)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            raise HTTPException(status_code=404, detail="Report not found")

        return {
            "id": row.id,
            "query": row.query,
            "report": row.report,
            "evaluation_score": row.evaluation_score,
            "retry_count": row.retry_count,
            "thought_trace": row.thought_trace,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
