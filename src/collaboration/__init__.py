"""Collaboration package for Prompt2Product (Faz 6.5).

Provides Issue and PR providers, adapters, and models for GitHub/local work management.
"""
from src.collaboration.adapter import ReviewToIssueAdapter
from src.collaboration.issues import GitHubIssueProvider, IssueProvider, LocalIssueStore
from src.collaboration.models import (
    Issue,
    IssueSeverity,
    IssueStatus,
    PRStatus,
    PRType,
    PullRequest,
)
from src.collaboration.pull_requests import GitHubPRProvider, LocalPRStore, PRProvider

__all__ = [
    "Issue",
    "IssueSeverity",
    "IssueStatus",
    "PullRequest",
    "PRStatus",
    "PRType",
    "IssueProvider",
    "LocalIssueStore",
    "GitHubIssueProvider",
    "PRProvider",
    "LocalPRStore",
    "GitHubPRProvider",
    "ReviewToIssueAdapter",
]
