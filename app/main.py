from fastapi import FastAPI

from .database import Base, engine
from .routers import auth, tasks, analytics

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Task Management API")

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
