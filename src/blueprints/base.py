"""Blueprint interface for project scaffolding and infrastructure generation (docs/01 §8, docs/08 §Faz 7)."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from src.models.enums import TargetType
from src.models.project import ProjectSpec
from src.workspace.workspace import Workspace


class Blueprint(ABC):
    """Abstract Blueprint defining project templates and infrastructure generators."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier of the blueprint (e.g. 'fastapi', 'nextjs')."""
        pass

    @property
    @abstractmethod
    def targets(self) -> list[TargetType]:
        """Supported TargetTypes."""
        pass

    @abstractmethod
    def generate_scaffold(self, workspace: Workspace, spec: ProjectSpec) -> list[Path]:
        """Generates standard project source code and directory layout."""
        pass

    @abstractmethod
    def generate_infra(self, workspace: Workspace, spec: ProjectSpec) -> list[Path]:
        """Generates Dockerfile, docker-compose.yml, and environment configs."""
        pass

    @abstractmethod
    def generate_tests(self, workspace: Workspace, spec: ProjectSpec) -> list[Path]:
        """Generates functional test suite for the generated project."""
        pass
