"""Planning package for Prompt2Product (Faz 6).

Contains DiscoveryEngine, ArchitecturePlanner, TaskDecomposer, and ACRManager.
"""
from src.planning.acr import ACRManager
from src.planning.architect import ArchitecturePlanner
from src.planning.decomposer import TaskDecomposer
from src.planning.discovery import DiscoveryEngine, slugify

__all__ = [
    "DiscoveryEngine",
    "slugify",
    "ArchitecturePlanner",
    "TaskDecomposer",
    "ACRManager",
]
