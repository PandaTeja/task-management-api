# Task Management API (FastAPI)

Backend assignment implementation using FastAPI, SQLAlchemy, and JWT-based auth.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate  #This is for Mac If Windows run .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

FastAPI interactive docs:

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

---

## Core Functionality

- Auth: user registration, login (`/auth/register`, `/auth/token`), JWT-based auth, `/auth/me`.
- RBAC roles: `admin`, `manager`, `member` (used for task update/delete permissions).
- Tasks: CRUD (`/tasks/`), subtasks (`parent_id`), collaborators, tags, and bulk update (`/tasks/bulk-update`).
- SQLite database auto-created as `taskmanager.db` in the project root via SQLAlchemy.

---

## Product Features Implemented

From the four suggested product features, the API implements **all four**, but the three I am explicitly choosing and highlighting (as “most valuable”) are:

1. **Filtering tasks by multiple criteria (status, priority, assignee, dates, tags)**
2. **Making tasks depend on other tasks (Task 2 blocked on Task 1)**
3. **API showing task distribution, and overdue tasks per user**

The **fourth feature** (timeline of task changes relevant to a user in the last N days) is also implemented as a bonus.

### Why these three features

- **Multi-criteria filtering** (`GET /tasks/`)
  - Real teams quickly accumulate many tasks.
  - Being able to filter by *status, priority, assignee, dates, and tags* is critical for day-to-day execution: triage, stand-ups, and personal focus.
  - It directly supports “working efficiently” for both individual contributors and managers.

- **Task dependencies** (`/tasks/{task_id}/dependencies/{depends_on_id}`)
  - Work items often block each other; surfacing explicit dependencies makes planning and coordination much easier.
  - It enables answering questions like “Why is this task blocked?” and supports realistic workflows (backend before frontend, design before implementation, etc.).

- **Task distribution & overdue per user** (`GET /analytics/task-distribution`)
  - Gives managers a quick view of workload balance and risk (who is overloaded, who has many overdue tasks).
  - This is highly actionable for rebalancing work and spotting bottlenecks.

- **Timeline of task changes** (`GET /analytics/timeline`)
  - Useful for individual contributors to review “what changed recently” on tasks relevant to them (as creator or assignee).
  - Helps with daily review and understanding the evolution of tasks.

---

## How to Run and Access APIs

1. **Create and activate virtualenv** (from project root):

   ```bash
   python -m venv .venv
   source .venv/bin/activate 
   ```

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Start the server**:

   ```bash
   uvicorn app.main:app --reload
   ```

4. **Open interactive docs**:

   - Swagger UI: `http://127.0.0.1:8000/docs`
   - ReDoc: `http://127.0.0.1:8000/redoc`

The SQLite database file `taskmanager.db` will be created automatically on first run.

---

## Basic Auth Flow for Testing

1. **Register a user** – `POST /auth/register` (Swagger → `auth` tag):

   Example body:

   ```json
   {
     "email": "admin@example.com",
     "full_name": "Admin User",
     "password": "Admin123!",
     "role": "admin"
   }
   ```

2. **Login to get JWT token** – `POST /auth/token`:

   - Content type: `application/x-www-form-urlencoded`.
   - Fields:
     - `username`: `admin@example.com`
     - `password`: `Admin123!`

   The response contains:

   ```json
   {
     "access_token": "<JWT>",
     "token_type": "bearer"
   }
   ```

3. **Authorize in Swagger**:

   - Click the green **Authorize** button.
   - For `OAuth2PasswordBearer`, enter:

     ```
     Bearer <JWT>
     ```

   - Click **Authorize** → **Close**.

4. **Check the current user** – `GET /auth/me`.

---

## Testing the Implemented Product Features

### 1. Filtering tasks by multiple criteria

Endpoint: **`GET /tasks/`**

Supported query parameters:

- `status`: repeatable, e.g. `?status=todo&status=in_progress`
- `priority`: repeatable, e.g. `?priority=high`
- `assignee_id`: repeatable, e.g. `?assignee_id=1&assignee_id=3`
- `tag`: repeatable, e.g. `?tag=backend&tag=frontend`
- `created_from`, `created_to`: ISO datetimes
- `due_from`, `due_to`: ISO datetimes

The filters are combined with **AND** logic; tags are applied via a join on the `tags` table.

Example: list all high-priority backend tasks assigned to user 3, due in December 2025:

```http
GET /tasks/?status=todo&priority=high&assignee_id=3&tag=backend&due_from=2025-12-01T00:00:00&due_to=2025-12-31T23:59:59
```

You can issue this request directly in Swagger by filling in the query params on `GET /tasks/`.

### 2. Task dependencies (Task 2 blocked on Task 1)

Endpoints:

- **Add dependency**: `POST /tasks/{task_id}/dependencies/{depends_on_id}`
- **List dependencies**: `GET /tasks/{task_id}/dependencies`

Example workflow:

1. Create Task 1 (e.g. "Design DB schema").
2. Create Task 2 (e.g. "Implement task CRUD APIs").
3. Make Task 2 depend on Task 1:

   ```http
   POST /tasks/2/dependencies/1
   ```

4. Check dependencies of Task 2:

   ```http
   GET /tasks/2/dependencies
   ```

This returns a list of task IDs that Task 2 depends on.

### 3. Task distribution & overdue tasks per user

Endpoint: **`GET /analytics/task-distribution`**

What it returns per assignee:

- `user_id`: ID of the assignee.
- `total_tasks`: count of tasks assigned to that user.
- `overdue_tasks`: tasks where `due_date < now`.

Example response snippet:

```json
[
  {
    "user_id": 3,
    "total_tasks": 5,
    "overdue_tasks": 2
  },
  {
    "user_id": 4,
    "total_tasks": 3,
    "overdue_tasks": 0
  }
]
```

This is useful for quickly seeing workload balance and overdue risk.

### 4. Timeline of task changes (bonus feature)

Endpoint: **`GET /analytics/timeline`**

Query parameter:

- `days` (optional, default `7`, allowed `1–90`)

The endpoint returns recent `TaskEvent` records for tasks where the current user is:

- The assignee, or
- The creator.

Events include creations, updates, and dependency additions, ordered from newest to oldest.

Example:

```http
GET /analytics/timeline?days=7
```

Each event contains task ID, event type, changed field, old value, and new value.

---

## Notes

- This project is designed as a focused backend assignment, not a production-ready system.
- Secrets like `SECRET_KEY` are hard-coded for simplicity; in real deployments they should come from environment variables or a secrets manager.

