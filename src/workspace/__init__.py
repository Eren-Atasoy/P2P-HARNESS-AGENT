"""Workspace package for Prompt2Product."""

from src.workspace.bootstrap import SmokeCheckResult, WorkspaceBootstrap
from src.workspace.git import GitError, GitManager, MergeConflictError
from src.workspace.scope import ScopeValidationResult, ScopeValidator
from src.workspace.workspace import PathTraversalError, Workspace

__all__ = [
    "GitError",
    "GitManager",
    "MergeConflictError",
    "PathTraversalError",
    "ScopeValidationResult",
    "ScopeValidator",
    "SmokeCheckResult",
    "Workspace",
    "WorkspaceBootstrap",
]
