"""Workload Mapping and Equivalence Translation Subsystem for CoreSync.

Strict Architectural Rule: This module MUST NOT import PySide6 or any Qt modules.
Translates unified logical workload configurations into:
1. Environment A: Real System executable datasets (NumPy) or TaskGraph DAGs.
2. Environment B: Virtual Lab discrete VirtualTask batches with matching computational weights and dependency models.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from engine.comparison.models import (
    ComparisonWorkloadConfig,
    ComparisonWorkloadType,
    RealSystemConfig,
    VirtualLabConfig,
)
from engine.data_parallel.operations import (
    generate_dataset,
    get_supported_operations,
)
from engine.data_parallel.partitioner import DataPartitioner
from engine.task_parallel.presets import (
    create_diamond_pipeline,
    create_fan_out_fan_in_pipeline,
    create_independent_benchmark_suite,
    create_scientific_suite,
)
from engine.task_parallel.task import Task, TaskPriority as RealTaskPriority
from engine.task_parallel.task_graph import TaskGraph
from engine.virtual_lab.virtual_task import TaskPriority as VirtualTaskPriority, VirtualTask


SUPPORTED_DATA_PARALLEL_OPS = {
    "transcendental": "Element-Wise Transcendental Math",
    "polynomial": "High-Order Polynomial Evaluation",
    "matrix_norms": "Matrix Frobenius & Spectral Norms",
    "prime_count": "Segmented Prime Sieve",
    "sum_of_squares": "Vector Sum of Squares Reduction",
}

SUPPORTED_TASK_PARALLEL_PRESETS = {
    "diamond": "Diamond Pipeline (4 Tasks)",
    "scientific": "Scientific Suite (7 Tasks)",
    "independent": "Independent Concurrency Suite (6 Tasks)",
    "fan_out_fan_in": "Fan-Out / Fan-In Pipeline (6 Tasks)",
}

# Relative computational weight factors per 10,000 items for virtual tick estimation
_DP_TICK_WEIGHTS = {
    "transcendental": 100,
    "polynomial": 80,
    "matrix_norms": 120,
    "prime_count": 200,
    "sum_of_squares": 60,
}


@dataclass
class MappedRealWorkload:
    """Artifacts prepared for execution on the Real System."""
    workload_type: ComparisonWorkloadType
    op_id: str
    dataset: Optional[np.ndarray] = None
    task_graph: Optional[TaskGraph] = None
    chunks: Optional[List[np.ndarray]] = None
    work_units: int = 0


@dataclass
class MappedVirtualWorkload:
    """Artifacts prepared for simulation inside the Virtual Lab."""
    workload_type: ComparisonWorkloadType
    tasks: List[VirtualTask]
    task_dependencies: Dict[str, List[str]] = field(default_factory=dict)
    total_nominal_ticks: int = 0
    work_units: int = 0


@dataclass
class WorkloadEquivalenceReport:
    """Certification of logical equivalence across both mapped workload models."""
    is_equivalent: bool
    workload_id: str
    workload_type: ComparisonWorkloadType
    real_work_units: int
    virtual_work_units: int
    logical_task_count: int
    partitioning_strategy: str
    details: str


def get_supported_workloads() -> Dict[str, Dict[str, str]]:
    """Return dictionary of all certified comparison workloads and presets."""
    return {
        "data_parallel": dict(SUPPORTED_DATA_PARALLEL_OPS),
        "task_parallel": dict(SUPPORTED_TASK_PARALLEL_PRESETS),
    }


def map_data_parallel_workload(
    config: ComparisonWorkloadConfig,
    real_workers: int,
    virtual_cores: int,
) -> Tuple[MappedRealWorkload, MappedVirtualWorkload, WorkloadEquivalenceReport]:
    """Map a data-parallel numerical workload to real arrays and virtual tasks.

    Args:
        config: Comparison workload configuration.
        real_workers: Worker process count for the Real System.
        virtual_cores: Virtual core count for the Virtual Lab.

    Returns:
        Tuple of (MappedRealWorkload, MappedVirtualWorkload, WorkloadEquivalenceReport).

    Raises:
        ValueError: If operation is unsupported or dataset size is non-positive.
    """
    op_id = config.workload_id
    if op_id not in SUPPORTED_DATA_PARALLEL_OPS:
        raise ValueError(
            f"Unsupported data-parallel comparison workload '{op_id}'. "
            f"Supported operations: {list(SUPPORTED_DATA_PARALLEL_OPS.keys())}"
        )

    size = max(100, int(config.dataset_size))

    # 1. Real System: generate dataset array and divide into chunks
    real_dataset = generate_dataset(op_id, size)
    w_count = max(1, real_workers)
    real_partitions = DataPartitioner.partition_array(real_dataset, w_count)
    real_chunks = [sub_arr for _, sub_arr in real_partitions]

    mapped_real = MappedRealWorkload(
        workload_type=ComparisonWorkloadType.DATA_PARALLEL,
        op_id=op_id,
        dataset=real_dataset,
        chunks=real_chunks,
        work_units=size,
    )

    # 2. Virtual Lab: map chunks into discrete VirtualTask items
    # In the Virtual Lab, each core or partition processes a slice of work
    v_task_count = max(1, min(w_count, virtual_cores * 2))
    v_partitions = DataPartitioner.partition_array(real_dataset, v_task_count)
    v_chunks = [sub_arr for _, sub_arr in v_partitions]

    base_weight = _DP_TICK_WEIGHTS.get(op_id, 100)
    virtual_tasks: List[VirtualTask] = []
    total_ticks = 0

    for idx, chunk in enumerate(v_chunks):
        chunk_len = len(chunk)
        # Ticks are strictly proportional to chunk item count
        ticks = max(10, int(round((chunk_len / 10_000.0) * base_weight)))
        t = VirtualTask(
            task_id=idx + 1,
            name=f"DP-Chunk-{idx + 1} ({chunk_len} items)",
            workload_type=f"DataParallel: {op_id}",
            total_ticks=ticks,
            remaining_ticks=ticks,
            priority=VirtualTaskPriority.MEDIUM,
        )
        virtual_tasks.append(t)
        total_ticks += ticks

    mapped_virtual = MappedVirtualWorkload(
        workload_type=ComparisonWorkloadType.DATA_PARALLEL,
        tasks=virtual_tasks,
        task_dependencies={},  # DP chunks are independent
        total_nominal_ticks=total_ticks,
        work_units=size,
    )

    report = WorkloadEquivalenceReport(
        is_equivalent=True,
        workload_id=op_id,
        workload_type=ComparisonWorkloadType.DATA_PARALLEL,
        real_work_units=size,
        virtual_work_units=size,
        logical_task_count=len(virtual_tasks),
        partitioning_strategy=f"Uniform array partitioning: {size:,} items across {w_count} real workers and {v_task_count} virtual chunk tasks.",
        details=f"Both environments process {size:,} items of '{SUPPORTED_DATA_PARALLEL_OPS[op_id]}' with matching relative workload intensity.",
    )

    return mapped_real, mapped_virtual, report


def map_task_parallel_workload(
    config: ComparisonWorkloadConfig,
) -> Tuple[MappedRealWorkload, MappedVirtualWorkload, WorkloadEquivalenceReport]:
    """Map a task-parallel DAG preset to a real TaskGraph and virtual tasks.

    Args:
        config: Comparison workload configuration.

    Returns:
        Tuple of (MappedRealWorkload, MappedVirtualWorkload, WorkloadEquivalenceReport).

    Raises:
        ValueError: If preset is unsupported.
    """
    preset_id = config.workload_id
    if preset_id not in SUPPORTED_TASK_PARALLEL_PRESETS:
        raise ValueError(
            f"Unsupported task-parallel comparison preset '{preset_id}'. "
            f"Supported presets: {list(SUPPORTED_TASK_PARALLEL_PRESETS.keys())}"
        )

    # 1. Real System: generate TaskGraph from verified presets
    if preset_id == "diamond":
        graph = create_diamond_pipeline()
    elif preset_id == "scientific":
        graph = create_scientific_suite()
    elif preset_id == "independent":
        graph = create_independent_benchmark_suite()
    elif preset_id == "fan_out_fan_in":
        graph = create_fan_out_fan_in_pipeline()
    else:
        raise ValueError(f"Unknown task parallel preset {preset_id}")

    mapped_real = MappedRealWorkload(
        workload_type=ComparisonWorkloadType.TASK_PARALLEL,
        op_id=preset_id,
        task_graph=graph,
        work_units=len(graph.tasks),
    )

    # 2. Virtual Lab: map real Task items to VirtualTask objects preserving DAG structure
    virtual_tasks: List[VirtualTask] = []
    task_dependencies: Dict[str, List[str]] = {}
    total_ticks = 0

    id_to_int: Dict[str, int] = {}
    for idx, (t_id, real_task) in enumerate(graph.tasks.items(), start=1):
        id_to_int[t_id] = idx

    for t_id, real_task in graph.tasks.items():
        # Map priority
        if real_task.priority in (RealTaskPriority.CRITICAL, RealTaskPriority.HIGH):
            v_prio = VirtualTaskPriority.HIGH
        elif real_task.priority == RealTaskPriority.LOW:
            v_prio = VirtualTaskPriority.LOW
        else:
            v_prio = VirtualTaskPriority.MEDIUM

        # Convert duration to nominal ticks: 0.1s -> 50 ticks
        dur = real_task.estimated_duration_s if real_task.estimated_duration_s > 0 else 0.1
        ticks = max(10, int(round(dur * 500)))

        v_t = VirtualTask(
            task_id=id_to_int[t_id],
            name=f"[{t_id}] {real_task.name}",
            workload_type=f"Task: {real_task.task_type}",
            total_ticks=ticks,
            remaining_ticks=ticks,
            priority=v_prio,
        )
        virtual_tasks.append(v_t)
        total_ticks += ticks
        task_dependencies[t_id] = list(real_task.dependencies)

    mapped_virtual = MappedVirtualWorkload(
        workload_type=ComparisonWorkloadType.TASK_PARALLEL,
        tasks=virtual_tasks,
        task_dependencies=task_dependencies,
        total_nominal_ticks=total_ticks,
        work_units=len(graph.tasks),
    )

    report = WorkloadEquivalenceReport(
        is_equivalent=True,
        workload_id=preset_id,
        workload_type=ComparisonWorkloadType.TASK_PARALLEL,
        real_work_units=len(graph.tasks),
        virtual_work_units=len(graph.tasks),
        logical_task_count=len(graph.tasks),
        partitioning_strategy=f"DAG Topology Preservation: {len(graph.tasks)} tasks with dependencies {dict(task_dependencies)}.",
        details=f"Both environments execute identical task definitions and dependency constraints for '{SUPPORTED_TASK_PARALLEL_PRESETS[preset_id]}'.",
    )

    return mapped_real, mapped_virtual, report


def map_workload(
    config: ComparisonWorkloadConfig,
    real_config: RealSystemConfig,
    virtual_config: VirtualLabConfig,
) -> Tuple[MappedRealWorkload, MappedVirtualWorkload, WorkloadEquivalenceReport]:
    """Unified entry point to map any supported comparison workload."""
    if config.workload_type == ComparisonWorkloadType.DATA_PARALLEL:
        return map_data_parallel_workload(config, real_config.worker_count, virtual_config.virtual_core_count)
    elif config.workload_type == ComparisonWorkloadType.TASK_PARALLEL:
        return map_task_parallel_workload(config)
    else:
        raise ValueError(f"Unsupported comparison workload type '{config.workload_type}'")
