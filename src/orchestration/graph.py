"""Task graph management, DAG validation, path conflict analysis, and wave computation."""
from collections import defaultdict, deque
from typing import Optional
from src.models.task import TaskContract


class CycleError(Exception):
    """Raised when a circular dependency is detected in the task graph."""
    pass


class MissingDependencyError(Exception):
    """Raised when a task depends on a task ID not present in the graph."""
    pass


def normalize_glob(pattern: str) -> str:
    """Normalizes a POSIX glob pattern to its directory/file prefix."""
    p = pattern.strip().replace("\\", "/")
    while p.endswith("/**"):
        p = p[:-3]
    while p.endswith("/*"):
        p = p[:-2]
    return p.rstrip("/")


def globs_overlap(glob_a: str, glob_b: str) -> bool:
    """
    Checks whether two glob paths overlap (i.e. could contain the same file).
    e.g. 'backend/api/**' and 'backend/**' -> True
         'backend/**' and 'frontend/**' -> False
         'src/a.py' and 'src/b.py' -> False
    """
    a = normalize_glob(glob_a)
    b = normalize_glob(glob_b)

    if not a or not b:
        return True  # Root level glob overlaps with everything

    if a == b:
        return True

    if a.startswith(b + "/") or b.startswith(a + "/"):
        return True

    return False


def paths_conflict(paths_a: list[str], paths_b: list[str]) -> bool:
    """Returns True if any path in paths_a overlaps with any path in paths_b."""
    for pa in paths_a:
        for pb in paths_b:
            if globs_overlap(pa, pb):
                return True
    return False


class TaskGraph:
    """Directed Acyclic Graph (DAG) of TaskContracts with path conflict-aware scheduling."""

    def __init__(self):
        self.tasks: dict[str, TaskContract] = {}

    def add_task(self, task: TaskContract):
        self.tasks[task.id] = task

    def get_task(self, task_id: str) -> Optional[TaskContract]:
        return self.tasks.get(task_id)

    def validate(self):
        """Validates that all dependencies exist and graph has no cycles."""
        for tid, task in self.tasks.items():
            for dep in task.depends_on:
                if dep not in self.tasks:
                    raise MissingDependencyError(f"Task '{tid}' depends on non-existent task '{dep}'")

        # Cycle detection using Kahn's algorithm
        in_degree = {tid: 0 for tid in self.tasks}
        adj = defaultdict(list)

        for tid, task in self.tasks.items():
            for dep in task.depends_on:
                adj[dep].append(tid)
                in_degree[tid] += 1

        queue = deque([tid for tid, deg in in_degree.items() if deg == 0])
        visited_count = 0

        while queue:
            node = queue.popleft()
            visited_count += 1
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited_count != len(self.tasks):
            # Find cycle nodes
            cycle_nodes = [tid for tid, deg in in_degree.items() if deg > 0]
            raise CycleError(f"Circular dependency detected involving tasks: {sorted(cycle_nodes)}")

    def compute_waves(self) -> list[list[str]]:
        """
        Computes parallel execution waves (docs/03 §2.1 & §2.2).
        Guarantees:
        1. All dependencies of a task are in strictly EARLIER waves.
        2. No two tasks in the same wave have overlapping allowed_paths.
        3. Deterministic order: ties broken by alphabetical task ID.
        """
        self.validate()

        if not self.tasks:
            return []

        # Track completed tasks by wave index
        task_wave_assigned: dict[str, int] = {}
        waves: list[list[str]] = []

        # Find topological level for each task
        remaining = set(self.tasks.keys())

        while remaining:
            # Candidate tasks whose dependencies are already assigned to previous waves
            candidates = []
            for tid in sorted(remaining):
                task = self.tasks[tid]
                deps_satisfied = all(dep in task_wave_assigned for dep in task.depends_on)
                if deps_satisfied:
                    # The earliest wave this task could belong to is max(dep_wave) + 1
                    min_wave = 0
                    if task.depends_on:
                        min_wave = max(task_wave_assigned[dep] for dep in task.depends_on) + 1
                    candidates.append((tid, min_wave))

            # Assign candidate tasks to waves, taking path conflicts into account
            assigned_this_round = False
            for tid, min_wave in candidates:
                task = self.tasks[tid]
                target_wave_idx = min_wave

                # Find the first wave >= min_wave that has no path conflict
                while True:
                    if target_wave_idx >= len(waves):
                        waves.append([])

                    # Check conflict with any task already in waves[target_wave_idx]
                    conflict = False
                    for other_tid in waves[target_wave_idx]:
                        other_task = self.tasks[other_tid]
                        if paths_conflict(task.allowed_paths, other_task.allowed_paths):
                            conflict = True
                            break

                    if not conflict:
                        waves[target_wave_idx].append(tid)
                        task_wave_assigned[tid] = target_wave_idx
                        remaining.remove(tid)
                        assigned_this_round = True
                        break
                    else:
                        target_wave_idx += 1

            if not assigned_this_round:
                raise RuntimeError("Failed to make progress in wave computation")

        # Sort task IDs within each wave for deterministic execution order (docs/03 §2.4)
        for wave in waves:
            wave.sort()

        # Remove any empty trailing waves
        return [w for w in waves if w]
