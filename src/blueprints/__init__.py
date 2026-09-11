"""Blueprints package for Prompt2Product (Faz 7 / Milestone 2).

Provides Blueprint interface and FastApiBlueprint Golden Blueprint.
"""
from src.blueprints.base import Blueprint
from src.blueprints.fastapi import FastApiBlueprint

__all__ = [
    "Blueprint",
    "FastApiBlueprint",
]
