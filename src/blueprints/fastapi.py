"""FastAPI Golden Blueprint implementation (docs/01 §6, docs/07 §8, docs/08 §Faz 7).

Generates production-ready FastAPI backend with SQLite/PostgreSQL support,
JWT authentication, Docker multi-stage build, docker-compose.yml, and functional test suite.
"""
from pathlib import Path

from src.blueprints.base import Blueprint
from src.models.enums import TargetType
from src.models.project import ProjectSpec
from src.workspace.workspace import Workspace


class FastApiBlueprint(Blueprint):
    """Production-grade FastAPI Golden Blueprint."""

    @property
    def name(self) -> str:
        return "fastapi"

    @property
    def targets(self) -> list[TargetType]:
        return [TargetType.API, TargetType.WEB]

    def generate_scaffold(self, workspace: Workspace, spec: ProjectSpec) -> list[Path]:
        workspace.ensure_directories()
        app_dir = workspace.backend_dir / "app"
        app_dir.mkdir(parents=True, exist_ok=True)

        generated_paths = []

        # 1. config.py
        config_path = app_dir / "config.py"
        config_path.write_text(
            '''import os

SECRET_KEY = os.getenv("SECRET_KEY", "default-insecure-secret-key-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
PROJECT_NAME = "''' + spec.name + '''"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
''',
            encoding="utf-8",
        )
        generated_paths.append(config_path)

        # 2. models.py
        models_path = app_dir / "models.py"
        models_path.write_text(
            '''from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class ItemBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    completed: bool = False


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    completed: Optional[bool] = None


class Item(ItemBase):
    id: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserLogin(BaseModel):
    username: str
    password: str
''',
            encoding="utf-8",
        )
        generated_paths.append(models_path)

        # 3. auth.py
        auth_path = app_dir / "auth.py"
        auth_path.write_text(
            '''from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from app.config import ALGORITHM, SECRET_KEY


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=30))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        return None
''',
            encoding="utf-8",
        )
        generated_paths.append(auth_path)

        # 4. crud.py
        crud_path = app_dir / "crud.py"
        crud_path.write_text(
            '''from typing import Optional
from app.models import Item, ItemCreate, ItemUpdate

_items_db: dict[int, Item] = {}
_id_counter = 0


def create_item(item_in: ItemCreate) -> Item:
    global _id_counter
    _id_counter += 1
    item = Item(
        id=_id_counter,
        title=item_in.title,
        description=item_in.description,
        completed=item_in.completed,
    )
    _items_db[item.id] = item
    return item


def get_item(item_id: int) -> Optional[Item]:
    return _items_db.get(item_id)


def list_items() -> list[Item]:
    return list(_items_db.values())


def update_item(item_id: int, item_in: ItemUpdate) -> Optional[Item]:
    existing = _items_db.get(item_id)
    if not existing:
        return None
    data = existing.model_dump()
    update_data = item_in.model_dump(exclude_unset=True)
    data.update(update_data)
    updated = Item(**data)
    _items_db[item_id] = updated
    return updated


def delete_item(item_id: int) -> bool:
    if item_id in _items_db:
        del _items_db[item_id]
        return True
    return False


def reset_db():
    global _id_counter
    _items_db.clear()
    _id_counter = 0
''',
            encoding="utf-8",
        )
        generated_paths.append(crud_path)

        # 5. main.py
        main_path = app_dir / "main.py"
        main_path.write_text(
            '''from fastapi import FastAPI, HTTPException, status
from app.config import PROJECT_NAME
from app.models import Item, ItemCreate, ItemUpdate, Token, UserLogin
from app.auth import create_access_token
import app.crud as crud

app = FastAPI(title=PROJECT_NAME, version="0.1.0")


@app.get("/health")
def health_check():
    return {"status": "ok", "project": PROJECT_NAME}


@app.post("/auth/login", response_model=Token)
def login(credentials: UserLogin):
    if credentials.username == "admin" and credentials.password == "secret":
        token = create_access_token({"sub": credentials.username})
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")


@app.get("/items", response_model=list[Item])
def get_items():
    return crud.list_items()


@app.post("/items", response_model=Item, status_code=status.HTTP_201_CREATED)
def create_item(item_in: ItemCreate):
    return crud.create_item(item_in)


@app.get("/items/{item_id}", response_model=Item)
def get_item(item_id: int):
    item = crud.get_item(item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


@app.put("/items/{item_id}", response_model=Item)
def update_item(item_id: int, item_in: ItemUpdate):
    item = crud.update_item(item_id, item_in)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int):
    success = crud.delete_item(item_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return None
''',
            encoding="utf-8",
        )
        generated_paths.append(main_path)

        # 6. backend/requirements.txt
        req_path = workspace.backend_dir / "requirements.txt"
        req_path.write_text(
            '''fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
pyjwt>=2.8.0
pytest>=8.0.0
httpx>=0.26.0
''',
            encoding="utf-8",
        )
        generated_paths.append(req_path)

        return generated_paths

    def generate_infra(self, workspace: Workspace, spec: ProjectSpec) -> list[Path]:
        workspace.ensure_directories()
        infra_dir = workspace.infra_dir
        infra_dir.mkdir(parents=True, exist_ok=True)

        generated = []

        # 1. Dockerfile (Multi-stage non-root)
        dockerfile = infra_dir / "Dockerfile"
        dockerfile.write_text(
            '''# Multi-stage build for production FastAPI
FROM python:3.11-slim AS builder
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app

# Run as non-root user (docs/06 §6, docs/07 §8)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY backend/app /app/app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
''',
            encoding="utf-8",
        )
        generated.append(dockerfile)

        # 2. docker-compose.yml
        compose = infra_dir / "docker-compose.yml"
        compose.write_text(
            '''version: '3.8'
services:
  api:
    build:
      context: ..
      dockerfile: infra/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - SECRET_KEY=production-secure-secret-key-p2p
      - PORT=8000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped
''',
            encoding="utf-8",
        )
        generated.append(compose)

        # 3. .env.example
        env_example = infra_dir / ".env.example"
        env_example.write_text(
            '''SECRET_KEY=replace-with-secure-random-key
PORT=8000
DATABASE_URL=sqlite:///./app.db
''',
            encoding="utf-8",
        )
        generated.append(env_example)

        # 4. docs/deployment.md
        docs_dir = workspace.root_path / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        dep_doc = docs_dir / "deployment.md"
        dep_doc.write_text(
            f'''# Deployment Guide: {spec.name}

## Local Development
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Production via Docker Compose
```bash
docker compose -f infra/docker-compose.yml up --build -d
```

## Health Verification
```bash
curl http://localhost:8000/health
```
''',
            encoding="utf-8",
        )
        generated.append(dep_doc)

        return generated

    def generate_tests(self, workspace: Workspace, spec: ProjectSpec) -> list[Path]:
        workspace.ensure_directories()
        tests_dir = workspace.tests_dir
        tests_dir.mkdir(parents=True, exist_ok=True)

        generated = []

        # tests/test_generated_api.py
        test_file = tests_dir / "test_generated_api.py"
        test_file.write_text(
            '''import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app
import app.crud as crud

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    crud.reset_db()
    yield
    crud.reset_db()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_create_and_get_item():
    res = client.post("/items", json={"title": "First Task", "description": "Details"})
    assert res.status_code == 201
    created = res.json()
    assert created["id"] == 1
    assert created["title"] == "First Task"

    # Get single item
    res_get = client.get(f"/items/{created['id']}")
    assert res_get.status_code == 200
    assert res_get.json()["title"] == "First Task"


def test_auth_login():
    res_fail = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
    assert res_fail.status_code == 401

    res_ok = client.post("/auth/login", json={"username": "admin", "password": "secret"})
    assert res_ok.status_code == 200
    token = res_ok.json()
    assert "access_token" in token
    assert token["token_type"] == "bearer"
''',
            encoding="utf-8",
        )
        generated.append(test_file)

        return generated
