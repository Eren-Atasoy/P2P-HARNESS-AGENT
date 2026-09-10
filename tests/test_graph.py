"""Tests for TaskGraph DAG validation, cycle detection, path conflicts, and wave computation."""
import pytest

from src.models import (
    AcceptanceCriterion,
    Capability,
    EstimatedSize,
    RiskLevel,
    TaskContract,
    VerifiedBy,
)
from src.orchestration.graph import (
    CycleError,
    MissingDependencyError,
    TaskGraph,
    globs_overlap,
    paths_conflict,
)


def make_task(tid: str, deps=None, allowed=None, forbidden=None) -> TaskContract:
    return TaskContract(
        id=tid,
        title=f"Task {tid}",
        capabilities=[Capability.BACKEND],
        risk=RiskLevel.LOW,
        depends_on=deps or [],
        intent=f"Intent for {tid}",
        acceptance_criteria=[
            AcceptanceCriterion(
                id="AC-1",
                statement="Works",
                verified_by=VerifiedBy.TEST,
                test_ref="tests/test_app.py::test_fn",
            )
        ],
        inputs=["docs/01"],
        allowed_paths=allowed or ["src/**"],
        forbidden_paths=forbidden or [],
        gates=["lint"],
        estimated_size=EstimatedSize.S,
        result_path=".p2p/result.json",
        acr_path=".p2p/acr/",
    )


def test_glob_overlap_detection():
    assert globs_overlap("backend/api/**", "backend/**") is True
    assert globs_overlap("backend/**", "backend/api/**") is True
    assert globs_overlap("backend/**", "frontend/**") is False
    assert globs_overlap("src/a.py", "src/b.py") is False
    assert globs_overlap("src/a.py", "src/**") is True
    assert globs_overlap("tests/api/**", "backend/api/**") is False


def test_paths_conflict():
    assert paths_conflict(["backend/api/**"], ["backend/**"]) is True
    assert paths_conflict(["backend/api/**"], ["frontend/**", "tests/**"]) is False


def test_missing_dependency_raises():
    graph = TaskGraph()
    graph.add_task(make_task("API-001", deps=["NON_EXISTENT-001"]))
    with pytest.raises(MissingDependencyError):
        graph.validate()


def test_cycle_detection():
    graph = TaskGraph()
    graph.add_task(make_task("A-001", deps=["B-001"]))
    graph.add_task(make_task("B-001", deps=["C-001"]))
    graph.add_task(make_task("C-001", deps=["A-001"]))  # Cycle A -> B -> C -> A
    with pytest.raises(CycleError):
        graph.validate()


def test_wave_computation_sequential_and_parallel():
    graph = TaskGraph()
    # Independent tasks with non-overlapping paths -> same wave (parallel)
    graph.add_task(make_task("API-001", allowed=["backend/**"]))
    graph.add_task(make_task("FE-001", allowed=["frontend/**"]))
    graph.add_task(make_task("DOC-001", allowed=["docs/**"]))

    waves = graph.compute_waves()
    assert len(waves) == 1
    assert waves[0] == ["API-001", "DOC-001", "FE-001"]


def test_wave_computation_path_conflict_forces_sequential():
    graph = TaskGraph()
    # No dependency, BUT overlapping paths -> forced into sequential waves!
    graph.add_task(make_task("API-001", allowed=["backend/**"]))
    graph.add_task(make_task("DB-001", allowed=["backend/models/**"]))

    waves = graph.compute_waves()
    assert len(waves) == 2
    # Alphabetical order breaks tie
    assert waves[0] == ["API-001"]
    assert waves[1] == ["DB-001"]


def test_wave_computation_dependencies_enforced():
    graph = TaskGraph()
    graph.add_task(make_task("DB-001", allowed=["backend/db/**"]))
    graph.add_task(make_task("API-001", deps=["DB-001"], allowed=["backend/api/**"]))
    graph.add_task(make_task("UI-001", deps=["API-001"], allowed=["frontend/**"]))

    waves = graph.compute_waves()
    assert len(waves) == 3
    assert waves[0] == ["DB-001"]
    assert waves[1] == ["API-001"]
    assert waves[2] == ["UI-001"]
