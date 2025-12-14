from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_current_user, get_db

router = APIRouter()


@router.get("/task-distribution", response_model=List[schemas.TaskDistribution])
def task_distribution(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    sub = (
        db.query(
            models.Task.assignee_id.label("user_id"),
            func.count(models.Task.id).label("total_tasks"),
            func.sum(
                case(
                    (models.Task.due_date < datetime.utcnow(), 1),
                    else_=0,
                )
            ).label("overdue_tasks"),
        )
        .filter(models.Task.assignee_id.is_not(None))
        .group_by(models.Task.assignee_id)
        .all()
    )

    return [
        schemas.TaskDistribution(
            user_id=row.user_id,
            total_tasks=row.total_tasks,
            overdue_tasks=row.overdue_tasks or 0,
        )
        for row in sub
    ]


@router.get("/timeline", response_model=List[schemas.TaskEventRead])
def timeline(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    since = datetime.utcnow() - timedelta(days=days)

    events = (
        db.query(models.TaskEvent)
        .join(models.Task)
        .filter(
            models.TaskEvent.created_at >= since,
            (
                (models.Task.assignee_id == current_user.id)
                | (models.Task.created_by_id == current_user.id)
            ),
        )
        .order_by(models.TaskEvent.created_at.desc())
        .all()
    )

    return events
