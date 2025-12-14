from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_current_user, get_db

router = APIRouter()


def _apply_task_updates(task: models.Task, data: schemas.TaskUpdate, db: Session, user_id: int):
    changed_fields = []

    def set_attr(field: str, value):
        old = getattr(task, field)
        if value is not None and value != old:
            setattr(task, field, value)
            changed_fields.append((field, old, value))

    set_attr("title", data.title)
    set_attr("description", data.description)
    set_attr("status", data.status)
    set_attr("priority", data.priority)
    set_attr("due_date", data.due_date)
    set_attr("assignee_id", data.assignee_id)
    set_attr("parent_id", data.parent_id)

    if data.tag_names is not None:
        task.tags.clear()
        for name in data.tag_names:
            tag = db.query(models.Tag).filter(models.Tag.name == name).first()
            if not tag:
                tag = models.Tag(name=name)
                db.add(tag)
            task.tags.append(tag)
        changed_fields.append(("tags", None, ",".join(data.tag_names)))

    if data.collaborator_ids is not None:
        task.collaborators.clear()
        if data.collaborator_ids:
            users = (
                db.query(models.User)
                .filter(models.User.id.in_(data.collaborator_ids))
                .all()
            )
            task.collaborators.extend(users)
        changed_fields.append(
            ("collaborators", None, ",".join(map(str, data.collaborator_ids)))
        )

    for field, old, new in changed_fields:
        event = models.TaskEvent(
            task_id=task.id,
            user_id=user_id,
            event_type="update",
            field=field,
            old_value=str(old) if old is not None else None,
            new_value=str(new) if new is not None else None,
        )
        db.add(event)


@router.post("/", response_model=schemas.TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(
    task_in: schemas.TaskCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    task = models.Task(
        title=task_in.title,
        description=task_in.description,
        status=task_in.status or models.TaskStatusEnum.TODO.value,
        priority=task_in.priority or models.TaskPriorityEnum.MEDIUM.value,
        due_date=task_in.due_date,
        created_by_id=current_user.id,
        assignee_id=task_in.assignee_id,
        parent_id=task_in.parent_id,
    )

    if task_in.tag_names:
        for name in task_in.tag_names:
            tag = db.query(models.Tag).filter(models.Tag.name == name).first()
            if not tag:
                tag = models.Tag(name=name)
                db.add(tag)
            task.tags.append(tag)

    if task_in.collaborator_ids:
        users = (
            db.query(models.User)
            .filter(models.User.id.in_(task_in.collaborator_ids))
            .all()
        )
        task.collaborators.extend(users)

    db.add(task)
    db.commit()
    db.refresh(task)

    event = models.TaskEvent(
        task_id=task.id,
        user_id=current_user.id,
        event_type="create",
        field=None,
        old_value=None,
        new_value=None,
    )
    db.add(event)
    db.commit()

    return task


@router.get("/{task_id}", response_model=schemas.TaskRead)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/", response_model=List[schemas.TaskRead])
def list_tasks(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    status_in: Optional[List[str]] = Query(None, alias="status"),
    priority_in: Optional[List[str]] = Query(None, alias="priority"),
    assignee_id_in: Optional[List[int]] = Query(None, alias="assignee_id"),
    tag_in: Optional[List[str]] = Query(None, alias="tag"),
    created_from: Optional[datetime] = None,
    created_to: Optional[datetime] = None,
    due_from: Optional[datetime] = None,
    due_to: Optional[datetime] = None,
):
    q = db.query(models.Task)

    conditions = []
    if status_in:
        conditions.append(models.Task.status.in_(status_in))
    if priority_in:
        conditions.append(models.Task.priority.in_(priority_in))
    if assignee_id_in:
        conditions.append(models.Task.assignee_id.in_(assignee_id_in))
    if created_from:
        conditions.append(models.Task.created_at >= created_from)
    if created_to:
        conditions.append(models.Task.created_at <= created_to)
    if due_from:
        conditions.append(models.Task.due_date >= due_from)
    if due_to:
        conditions.append(models.Task.due_date <= due_to)

    if conditions:
        q = q.filter(and_(*conditions))

    if tag_in:
        q = q.join(models.Task.tags).filter(models.Tag.name.in_(tag_in))

    return q.all()


@router.patch("/{task_id}", response_model=schemas.TaskRead)
def update_task(
    task_id: int,
    task_in: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Simple RBAC: creator, assignee, or admin/manager can update
    if current_user.role not in ("admin", "manager") and current_user.id not in (
        task.created_by_id,
        task.assignee_id,
    ):
        raise HTTPException(status_code=403, detail="Not allowed to update this task")

    _apply_task_updates(task, task_in, db, current_user.id)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if current_user.role not in ("admin", "manager") and current_user.id != task.created_by_id:
        raise HTTPException(status_code=403, detail="Not allowed to delete this task")

    db.delete(task)
    db.commit()
    return


@router.post("/bulk-update", response_model=List[schemas.TaskRead])
def bulk_update_tasks(
    payload: schemas.BulkTaskUpdateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    task_ids = [item.id for item in payload.items]
    tasks = db.query(models.Task).filter(models.Task.id.in_(task_ids)).all()
    tasks_by_id = {t.id: t for t in tasks}

    updated = []
    for item in payload.items:
        task = tasks_by_id.get(item.id)
        if not task:
            continue
        if current_user.role not in ("admin", "manager") and current_user.id not in (
            task.created_by_id,
            task.assignee_id,
        ):
            continue

        data = schemas.TaskUpdate(**item.model_dump())
        _apply_task_updates(task, data, db, current_user.id)
        updated.append(task)

    db.commit()
    for t in updated:
        db.refresh(t)
    return updated


@router.post("/{task_id}/dependencies/{depends_on_id}", status_code=status.HTTP_201_CREATED)
def add_dependency(
    task_id: int,
    depends_on_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if task_id == depends_on_id:
        raise HTTPException(status_code=400, detail="Task cannot depend on itself")

    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    depends_on = db.query(models.Task).filter(models.Task.id == depends_on_id).first()
    if not task or not depends_on:
        raise HTTPException(status_code=404, detail="Task not found")

    dep = (
        db.query(models.TaskDependency)
        .filter(
            models.TaskDependency.task_id == task_id,
            models.TaskDependency.depends_on_id == depends_on_id,
        )
        .first()
    )
    if dep:
        return {"detail": "Dependency already exists"}

    dep = models.TaskDependency(task_id=task_id, depends_on_id=depends_on_id)
    db.add(dep)
    db.commit()

    event = models.TaskEvent(
        task_id=task_id,
        user_id=current_user.id,
        event_type="add_dependency",
        field="depends_on",
        old_value=None,
        new_value=str(depends_on_id),
    )
    db.add(event)
    db.commit()

    return {"detail": "Dependency added"}


@router.get("/{task_id}/dependencies", response_model=List[int])
def list_dependencies(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    deps = (
        db.query(models.TaskDependency)
        .filter(models.TaskDependency.task_id == task_id)
        .all()
    )
    return [d.depends_on_id for d in deps]
