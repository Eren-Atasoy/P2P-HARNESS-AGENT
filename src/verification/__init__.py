"""Verification package for Prompt2Product."""

from src.models.result import GateFailure, GateResult
from src.verification.a11y import A11yParser, A11yScanner
from src.verification.config import GateDefinition, GatesConfig
from src.verification.parsers import (
    BaseOutputParser,
    EslintParser,
    NoneParser,
    PlaywrightParser,
    PytestParser,
    RuffParser,
    TscParser,
    get_parser,
)
from src.verification.regression import ImpactAnalyzer
from src.verification.runner import GateRunner
from src.verification.tautology import TautologyScanner

__all__ = [
    "A11yParser",
    "A11yScanner",
    "BaseOutputParser",
    "EslintParser",
    "GateDefinition",
    "GateFailure",
    "GateResult",
    "GateRunner",
    "GatesConfig",
    "ImpactAnalyzer",
    "NoneParser",
    "PlaywrightParser",
    "PytestParser",
    "RuffParser",
    "TautologyScanner",
    "TscParser",
    "get_parser",
]
