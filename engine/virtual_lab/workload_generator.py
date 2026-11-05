"""Virtual workload generator creating synthetic tasks for the Virtual Lab."""

import random
from typing import List

from engine.virtual_lab.virtual_task import TaskPriority, VirtualTask


class VirtualWorkloadGenerator:
    """Generates configurable synthetic task batches for Virtual Lab experiments."""

    WORKLOAD_TYPES = [
        "Matrix Multiplication",
        "Fast Fourier Transform",
        "Raytracing Shading",
        "QuickSort Partition",
        "Prime Factorization",
        "Data Compression",
    ]

    @classmethod
    def generate_batch(
        cls,
        count: int = 12,
        duration_preset: str = "medium",  # "short", "medium", "long", "mixed"
        priority_mode: str = "mixed",     # "mixed", "all_high", "all_medium", "all_low"
        random_seed: int = 42,
        burst_range: tuple = None,
    ) -> List[VirtualTask]:
        """Generate a reproducible list of virtual tasks."""
        rng = random.Random(random_seed)
        tasks: List[VirtualTask] = []

        duration_ranges = {
            "short": (20, 60),
            "medium": (60, 150),
            "long": (150, 350),
        }

        for i in range(count):
            task_id = i + 1
            w_type = rng.choice(cls.WORKLOAD_TYPES)

            # Determine ticks
            if burst_range is not None:
                ticks = rng.randint(*burst_range)
            elif duration_preset == "mixed":
                chosen_range = rng.choice(list(duration_ranges.values()))
                ticks = rng.randint(*chosen_range)
            else:
                ticks = rng.randint(*duration_ranges.get(duration_preset, (60, 150)))

            # Determine priority
            if priority_mode == "all_high":
                prio = TaskPriority.HIGH
            elif priority_mode == "all_low":
                prio = TaskPriority.LOW
            elif priority_mode == "all_medium":
                prio = TaskPriority.MEDIUM
            else:
                prio = rng.choice([TaskPriority.HIGH, TaskPriority.MEDIUM, TaskPriority.LOW])

            task = VirtualTask(
                task_id=task_id,
                name=f"Task-{task_id} ({w_type[:10]})",
                workload_type=w_type,
                total_ticks=ticks,
                remaining_ticks=ticks,
                priority=prio,
            )
            tasks.append(task)

        return tasks
