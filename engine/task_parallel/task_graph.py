"""Directed Acyclic Graph (DAG) Engine for Task Parallelism.

Strict Architectural Rule: This module MUST NOT import PySide6 or any Qt modules.
Enforces dependency ordering, cycle detection, ready-task releases, failure cascades, and deadlock checks.
"""

from collections import deque
import logging
from typing import Dict, List, Optional, Set, Tuple

from engine.task_parallel.task import Task, TaskStatus

logger = logging.getLogger("CoreSync.TaskParallel.TaskGraph")


class TaskGraph:
    """Manages DAG structure, topological ordering, and dynamic state transitions."""

    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        # child_id -> set of prerequisite task_ids
        self.dependencies: Dict[str, Set[str]] = {}
        # parent_id -> set of dependent child task_ids
        self.dependents: Dict[str, Set[str]] = {}

    def add_task(self, task: Task) -> None:
        """Register a task and initialize its dependency sets."""
        if task.task_id in self.tasks:
            raise ValueError(f"Task with ID '{task.task_id}' already exists in graph.")
        self.tasks[task.task_id] = task
        self.dependencies[task.task_id] = set(task.dependencies)
        self.dependents[task.task_id] = set()

        # Update reverse mappings for prerequisites that were already registered
        for parent_id in task.dependencies:
            if parent_id in self.dependents:
                self.dependents[parent_id].add(task.task_id)

    def add_dependency(self, child_id: str, parent_id: str) -> None:
        """Add a directed edge from parent_id to child_id (child depends on parent)."""
        if child_id not in self.tasks:
            raise KeyError(f"Child task '{child_id}' does not exist in graph.")
        if parent_id not in self.tasks:
            raise KeyError(f"Parent task '{parent_id}' does not exist in graph.")
        if child_id == parent_id:
            raise ValueError(f"Self-dependency detected: Task '{child_id}' cannot depend on itself.")

        self.dependencies[child_id].add(parent_id)
        self.dependents[parent_id].add(child_id)
        if parent_id not in self.tasks[child_id].dependencies:
            self.tasks[child_id].dependencies.append(parent_id)

    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate that all dependency IDs exist and the graph contains no cycles."""
        # 1. Check for missing dependency references
        for child_id, parents in self.dependencies.items():
            for parent_id in parents:
                if parent_id not in self.tasks:
                    return False, f"Task '{child_id}' depends on non-existent task '{parent_id}'."

        # 2. Check for cycles via topological sort
        if self.has_cycle():
            return False, "Cycle detected in task dependency graph."

        return True, None

    def has_cycle(self) -> bool:
        """Return True if graph contains any directed cycle (using Kahn's algorithm)."""
        # In-degree counts
        in_degree: Dict[str, int] = {t_id: len(parents) for t_id, parents in self.dependencies.items()}
        queue = deque([t_id for t_id, deg in in_degree.items() if deg == 0])

        visited_count = 0
        while queue:
            node = queue.popleft()
            visited_count += 1
            for child in self.dependents.get(node, set()):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        return visited_count != len(self.tasks)

    def get_topological_order(self) -> List[str]:
        """Return task IDs sorted in valid topological execution order."""
        is_valid, err = self.validate()
        if not is_valid:
            raise ValueError(f"Cannot topologically sort invalid DAG: {err}")

        in_degree: Dict[str, int] = {t_id: len(parents) for t_id, parents in self.dependencies.items()}
        queue = deque([t_id for t_id, deg in in_degree.items() if deg == 0])

        order: List[str] = []
        while queue:
            node = queue.popleft()
            order.append(node)
            for child in self.dependents.get(node, set()):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        return order

    def initialize_statuses(self) -> None:
        """Transition root tasks to READY and dependent tasks to BLOCKED."""
        is_valid, err = self.validate()
        if not is_valid:
            raise ValueError(f"DAG validation failed: {err}")

        for task_id, task in self.tasks.items():
            parent_ids = self.dependencies.get(task_id, set())
            if not parent_ids:
                task.transition_to(TaskStatus.READY)
            else:
                task.transition_to(TaskStatus.BLOCKED)

    def get_ready_tasks(self) -> List[Task]:
        """Return all tasks currently in READY state."""
        return [t for t in self.tasks.values() if t.status == TaskStatus.READY]

    def on_task_completed(self, task_id: str) -> List[Task]:
        """Handle task completion: unblock and return child tasks whose prerequisites are now all COMPLETED."""
        if task_id not in self.tasks:
            return []

        newly_ready: List[Task] = []
        for child_id in self.dependents.get(task_id, set()):
            child_task = self.tasks[child_id]
            if child_task.status == TaskStatus.BLOCKED:
                # Check if all prerequisites are completed
                parents = self.dependencies.get(child_id, set())
                all_done = all(self.tasks[p].status == TaskStatus.COMPLETED for p in parents)
                if all_done:
                    child_task.transition_to(TaskStatus.READY)
                    newly_ready.append(child_task)
                    logger.debug(f"Unblocked task '{child_id}' -> READY")

        return newly_ready

    def on_task_failed(self, task_id: str, error_message: str) -> List[Task]:
        """Handle task failure: cascade failure or permanent blocked state to all descendants."""
        affected: List[Task] = []
        queue = deque(list(self.dependents.get(task_id, set())))
        visited = set()

        while queue:
            child_id = queue.popleft()
            if child_id in visited:
                continue
            visited.add(child_id)

            child_task = self.tasks[child_id]
            if not child_task.is_terminal():
                reason = f"Prerequisite task '{task_id}' failed: {error_message}"
                child_task.transition_to(TaskStatus.FAILED, reason=reason)
                affected.append(child_task)
                logger.warning(f"Cascaded failure to dependent task '{child_id}': {reason}")

            # Enqueue further descendants
            for grandchild_id in self.dependents.get(child_id, set()):
                if grandchild_id not in visited:
                    queue.append(grandchild_id)

        return affected

    def on_task_cancelled(self, task_id: str) -> List[Task]:
        """Handle task cancellation: cascade cancellation to all unfinished descendants."""
        affected: List[Task] = []
        queue = deque(list(self.dependents.get(task_id, set())))
        visited = set()

        while queue:
            child_id = queue.popleft()
            if child_id in visited:
                continue
            visited.add(child_id)

            child_task = self.tasks[child_id]
            if not child_task.is_terminal():
                reason = f"Prerequisite task '{task_id}' was cancelled."
                child_task.transition_to(TaskStatus.CANCELLED, reason=reason)
                affected.append(child_task)

            for grandchild_id in self.dependents.get(child_id, set()):
                if grandchild_id not in visited:
                    queue.append(grandchild_id)

        return affected

    def check_deadlock(self, active_worker_count: int = 0) -> bool:
        """Check if remaining unfinished tasks cannot proceed due to unresolved dependencies."""
        unfinished = [t for t in self.tasks.values() if not t.is_terminal()]
        if not unfinished:
            return False  # All tasks are terminal; no deadlock

        ready_or_running = [
            t for t in unfinished
            if t.status in (TaskStatus.READY, TaskStatus.QUEUED, TaskStatus.RUNNING)
        ]

        # If there are unfinished tasks, but no tasks are ready or running, and no workers active -> Deadlock
        if not ready_or_running and active_worker_count == 0:
            return True

        return False

    def is_all_terminal(self) -> bool:
        """Return True if all tasks in the graph have reached a terminal state."""
        return all(t.is_terminal() for t in self.tasks.values())

    def clone(self) -> "TaskGraph":
        """Create an exact duplicate of this TaskGraph with fresh task lifecycle states."""
        new_graph = TaskGraph()
        for t_id, task in self.tasks.items():
            new_task = Task(
                task_id=task.task_id,
                name=task.name,
                task_type=task.task_type,
                params=dict(task.params),
                priority=task.priority,
                dependencies=list(task.dependencies),
                estimated_duration_s=task.estimated_duration_s,
                max_retries=task.max_retries,
            )
            new_graph.add_task(new_task)
        return new_graph

    def get_statistics(self) -> Dict[str, int]:
        """Return summary count of tasks in each status."""
        stats = {s.value: 0 for s in TaskStatus}
        for t in self.tasks.values():
            stats[t.status.value] += 1
        return stats

