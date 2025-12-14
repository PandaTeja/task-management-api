from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


task_collaborators = Table(
    "task_collaborators",
    Base.metadata,
    Column("task_id", ForeignKey("tasks.id"), primary_key=True),
    Column("user_id", ForeignKey("users.id"), primary_key=True),
)


task_tags = Table(
    "task_tags",
    Base.metadata,
    Column("task_id", ForeignKey("tasks.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
)


class UserRoleEnum(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"


class TaskStatusEnum(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


class TaskPriorityEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), nullable=False, default=UserRoleEnum.MEMBER.value)
    is_active = Column(Boolean, default=True)

    tasks_created = relationship("Task", back_populates="created_by", foreign_keys="Task.created_by_id")
    tasks_assigned = relationship("Task", back_populates="assignee", foreign_keys="Task.assignee_id")
    collaborations = relationship(
        "Task",
        secondary=task_collaborators,
        back_populates="collaborators",
    )


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)

    tasks = relationship("Task", secondary=task_tags, back_populates="tags")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default=TaskStatusEnum.TODO.value, index=True)
    priority = Column(String(50), default=TaskPriorityEnum.MEDIUM.value, index=True)
    due_date = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    parent_id = Column(Integer, ForeignKey("tasks.id"), nullable=True, index=True)

    created_by = relationship("User", foreign_keys=[created_by_id], back_populates="tasks_created")
    assignee = relationship("User", foreign_keys=[assignee_id], back_populates="tasks_assigned")

    parent = relationship("Task", remote_side=[id], backref="subtasks")

    collaborators = relationship(
        "User",
        secondary=task_collaborators,
        back_populates="collaborations",
    )

    tags = relationship("Tag", secondary=task_tags, back_populates="tasks")


class TaskDependency(Base):
    __tablename__ = "task_dependencies"
    __table_args__ = (
        UniqueConstraint("task_id", "depends_on_id", name="uq_task_depends_on"),
    )

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    depends_on_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)

    task = relationship("Task", foreign_keys=[task_id], backref="dependencies")
    depends_on = relationship("Task", foreign_keys=[depends_on_id], backref="dependants")


class TaskEvent(Base):
    __tablename__ = "task_events"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    event_type = Column(String(50), nullable=False)
    field = Column(String(50), nullable=True)
    old_value = Column(String(255), nullable=True)
    new_value = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    task = relationship("Task", backref="events")
    user = relationship("User")
