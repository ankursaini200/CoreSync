"""Tests for CoreSync Phase 10 Workload Mapper across Real and Virtual Environments."""

import pytest
import numpy as np
from engine.comparison.models import (
    ComparisonWorkloadConfig,
    ComparisonWorkloadType,
    RealSystemConfig,
    VirtualLabConfig,
)
from engine.comparison.workload_mapper import (
    SUPPORTED_DATA_PARALLEL_OPS,
    SUPPORTED_TASK_PARALLEL_PRESETS,
    map_workload,
    map_data_parallel_workload,
    map_task_parallel_workload,
    get_supported_workloads,
)


def test_supported_kernels_and_presets_lists():
    """Verify that required operations and presets are officially supported."""
    assert "transcendental" in SUPPORTED_DATA_PARALLEL_OPS
    assert "polynomial" in SUPPORTED_DATA_PARALLEL_OPS
    assert "matrix_norms" in SUPPORTED_DATA_PARALLEL_OPS
    assert "prime_count" in SUPPORTED_DATA_PARALLEL_OPS
    assert "sum_of_squares" in SUPPORTED_DATA_PARALLEL_OPS

    assert "diamond" in SUPPORTED_TASK_PARALLEL_PRESETS
    assert "scientific" in SUPPORTED_TASK_PARALLEL_PRESETS
    assert "independent" in SUPPORTED_TASK_PARALLEL_PRESETS
    assert "fan_out_fan_in" in SUPPORTED_TASK_PARALLEL_PRESETS

    catalog = get_supported_workloads()
    assert "data_parallel" in catalog
    assert "task_parallel" in catalog


def test_data_parallel_mapping_transcendental():
    """Verify mapping of Data Parallel transcendental operation to real and virtual workloads."""
    workload_cfg = ComparisonWorkloadConfig(
        workload_type=ComparisonWorkloadType.DATA_PARALLEL,
        workload_id="transcendental",
        workload_name="Transcendental Functions",
        dataset_size=4000,
    )
    real_cfg = RealSystemConfig(worker_count=4)
    virt_cfg = VirtualLabConfig(virtual_core_count=4)

    mapped_real, mapped_virt, report = map_workload(workload_cfg, real_cfg, virt_cfg)

    # 1. Real Workload Verification
    assert mapped_real.op_id == "transcendental"
    assert len(mapped_real.dataset) == 4000
    assert isinstance(mapped_real.dataset, np.ndarray)
    assert len(mapped_real.chunks) == 4

    # 2. Virtual Workload Verification
    assert len(mapped_virt.tasks) == 4
    for idx, task in enumerate(mapped_virt.tasks, start=1):
        assert task.task_id == idx
        assert task.total_ticks > 0
        assert "DP-Chunk" in task.name

    # 3. Equivalence Report
    assert report.is_equivalent is True


def test_task_parallel_mapping_diamond():
    """Verify mapping of Task Parallel diamond preset to DAG and virtual tasks."""
    workload_cfg = ComparisonWorkloadConfig(
        workload_type=ComparisonWorkloadType.TASK_PARALLEL,
        workload_id="diamond",
        workload_name="Diamond DAG",
    )
    real_cfg = RealSystemConfig(worker_count=4)
    virt_cfg = VirtualLabConfig(virtual_core_count=4)

    mapped_real, mapped_virt, report = map_workload(workload_cfg, real_cfg, virt_cfg)

    # 1. Real DAG Verification
    tasks = mapped_real.task_graph.tasks
    assert len(tasks) == 4
    assert set(tasks.keys()) == {"t1_init", "t2_matrix", "t3_primes", "t4_reduce"}

    task_reduce = tasks["t4_reduce"]
    assert set(task_reduce.dependencies) == {"t2_matrix", "t3_primes"}

    # 2. Virtual Tasks Verification
    assert len(mapped_virt.tasks) == 4
    assert set(mapped_virt.task_dependencies["t4_reduce"]) == {"t2_matrix", "t3_primes"}
    assert report.is_equivalent is True


def test_input_deep_cloning_and_isolation():
    """Verify that inputs mapped for Real and Virtual execution are independent deep copies."""
    workload_cfg = ComparisonWorkloadConfig(
        workload_type=ComparisonWorkloadType.DATA_PARALLEL,
        workload_id="sum_of_squares",
        workload_name="Sum of Squares",
        dataset_size=1000,
    )
    real_cfg = RealSystemConfig(worker_count=2)
    virt_cfg = VirtualLabConfig(virtual_core_count=2)

    mapped_real1, _, _ = map_workload(workload_cfg, real_cfg, virt_cfg)
    mapped_real2, _, _ = map_workload(workload_cfg, real_cfg, virt_cfg)

    # Mutate data in first workload
    mapped_real1.dataset[0] = 999999.0
    assert mapped_real2.dataset[0] != 999999.0


def test_unsupported_workload_rejection():
    """Verify that invalid operation names or unsupported types raise ValueError."""
    workload_invalid_dp = ComparisonWorkloadConfig(
        workload_type=ComparisonWorkloadType.DATA_PARALLEL,
        workload_id="non_existent_kernel",
        workload_name="Invalid Kernel",
        dataset_size=1000,
    )
    with pytest.raises(ValueError, match="Unsupported data-parallel comparison workload"):
        map_data_parallel_workload(workload_invalid_dp, real_workers=2, virtual_cores=2)

    workload_invalid_tp = ComparisonWorkloadConfig(
        workload_type=ComparisonWorkloadType.TASK_PARALLEL,
        workload_id="invalid_preset",
        workload_name="Invalid Preset",
    )
    with pytest.raises(ValueError, match="Unsupported task-parallel comparison preset"):
        map_task_parallel_workload(workload_invalid_tp)
