from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: int
    role: str


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str
    role: str = "member"


class UserRead(UserBase):
    id: int
    role: str

    class Config:
        from_attributes = True


class TagRead(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class TaskBase(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    assignee_id: Optional[int] = None
    parent_id: Optional[int] = None
    tag_names: Optional[List[str]] = None
    collaborator_ids: Optional[List[int]] = None


class TaskCreate(TaskBase):
    title: str


class TaskUpdate(TaskBase):
    pass


class TaskRead(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: str
    priority: str
    due_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    created_by_id: int
    assignee_id: Optional[int]
    parent_id: Optional[int]
    tags: List[TagRead] = []
    collaborator_ids: List[int] = []

    class Config:
        from_attributes = True


class BulkTaskUpdateItem(BaseModel):
    id: int
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee_id: Optional[int] = None


class BulkTaskUpdateRequest(BaseModel):
    items: List[BulkTaskUpdateItem]


class TaskFilter(BaseModel):
    statuses: Optional[List[str]] = None
    priorities: Optional[List[str]] = None
    assignee_ids: Optional[List[int]] = None
    tag_names: Optional[List[str]] = None
    created_from: Optional[datetime] = None
    created_to: Optional[datetime] = None
    due_from: Optional[datetime] = None
    due_to: Optional[datetime] = None


class TaskDistribution(BaseModel):
    user_id: int
    total_tasks: int
    overdue_tasks: int


class TaskEventRead(BaseModel):
    id: int
    task_id: int
    user_id: Optional[int]
    event_type: str
    field: Optional[str]
    old_value: Optional[str]
    new_value: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
