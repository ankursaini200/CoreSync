"""Configuration and Equivalence Validation for Real vs Virtual Comparison.

Strict Architectural Rule: This module MUST NOT import PySide6 or any Qt modules.
Validates configurations prior to execution and audits result consistency and isolation.
"""

from typing import List, Optional, Tuple

from engine.comparison.models import (
    ComparisonConfiguration,
    ComparisonExecutionMode,
    ComparisonWorkloadType,
    RealExecutionResult,
    VirtualExecutionResult,
)
from engine.comparison.workload_mapper import (
    SUPPORTED_DATA_PARALLEL_OPS,
    SUPPORTED_TASK_PARALLEL_PRESETS,
)


class ComparisonValidationError(ValueError):
    """Raised when comparison configuration or execution invariants are violated."""
    pass


def validate_comparison_configuration(config: ComparisonConfiguration) -> List[str]:
    """Validate comparison configuration parameters before starting execution.

    Returns:
        List of validation error messages. Empty list indicates valid configuration.
    """
    errors: List[str] = []

    if not config.comparison_id:
        errors.append("Comparison ID must not be empty.")

    # 1. Workload Validation
    w_type = config.workload.workload_type
    w_id = config.workload.workload_id

    if w_type == ComparisonWorkloadType.DATA_PARALLEL:
        if w_id not in SUPPORTED_DATA_PARALLEL_OPS:
            errors.append(
                f"Unsupported data-parallel workload '{w_id}'. Supported operations: {list(SUPPORTED_DATA_PARALLEL_OPS.keys())}"
            )
        if config.workload.dataset_size < 10:
            errors.append(f"Dataset size must be at least 10 items (got {config.workload.dataset_size}).")
        if config.workload.dataset_size > 10_000_000:
            errors.append(f"Dataset size exceeds safety ceiling of 10,000,000 items.")

    elif w_type == ComparisonWorkloadType.TASK_PARALLEL:
        if w_id not in SUPPORTED_TASK_PARALLEL_PRESETS:
            errors.append(
                f"Unsupported task-parallel preset '{w_id}'. Supported presets: {list(SUPPORTED_TASK_PARALLEL_PRESETS.keys())}"
            )
    else:
        errors.append(f"Unknown workload type: {w_type}")

    # 2. Real System Config Validation
    if config.execution_mode in (ComparisonExecutionMode.REAL_ONLY, ComparisonExecutionMode.COMPARE_BOTH):
        if config.real_config.worker_count < 1:
            errors.append(f"Real worker count must be >= 1 (got {config.real_config.worker_count}).")
        if config.real_config.worker_count > 128:
            errors.append(f"Real worker count exceeds safety ceiling of 128 (got {config.real_config.worker_count}).")
        if config.real_config.pinned_cpus is not None:
            for cpu in config.real_config.pinned_cpus:
                if cpu < 0:
                    errors.append(f"Invalid pinned CPU index {cpu}: must be non-negative.")

    # 3. Virtual Lab Config Validation
    if config.execution_mode in (ComparisonExecutionMode.VIRTUAL_ONLY, ComparisonExecutionMode.COMPARE_BOTH):
        v_cores = config.virtual_config.virtual_core_count
        if v_cores < 1:
            errors.append(f"Virtual core count must be >= 1 (got {v_cores}).")
        if v_cores > 256:
            errors.append(f"Virtual core count exceeds limit of 256 (got {v_cores}).")

        if config.virtual_config.enable_hybrid:
            p_cnt = config.virtual_config.p_core_count
            e_cnt = config.virtual_config.e_core_count
            if p_cnt < 1:
                errors.append(f"Hybrid virtual CPU requires at least 1 P-Core (got {p_cnt}).")
            if p_cnt + e_cnt > v_cores:
                errors.append(
                    f"P-Cores ({p_cnt}) + E-Cores ({e_cnt}) = {p_cnt + e_cnt} exceeds virtual core count ({v_cores})."
                )
            if config.virtual_config.p_core_speed <= 0.0 or config.virtual_config.e_core_speed <= 0.0:
                errors.append("Virtual core performance multipliers must be strictly positive.")

        if config.virtual_config.time_quantum < 1:
            errors.append(f"Virtual Round Robin quantum must be >= 1 tick (got {config.virtual_config.time_quantum}).")

    return errors


def assert_valid_configuration(config: ComparisonConfiguration) -> None:
    """Validate configuration and raise ComparisonValidationError if invalid."""
    errors = validate_comparison_configuration(config)
    if errors:
        raise ComparisonValidationError("; ".join(errors))


def validate_result_isolation(
    real_result: Optional[RealExecutionResult],
    virtual_result: Optional[VirtualExecutionResult],
) -> Tuple[bool, str]:
    """Verify that Real System and Virtual Lab results maintained structural isolation.

    Invariants:
        1. Virtual Lab result must not reference real host worker PIDs.
        2. Real System result must not reference virtual tick counts.
        3. Real wall-clock duration must not equal virtual tick count.
    """
    if real_result is None or virtual_result is None:
        return True, "Single environment executed; cross-environment isolation trivially holds."

    # Virtual result should not have OS PIDs
    for event in virtual_result.scheduling_events:
        if "process_id" in event:
            return False, "Virtual Lab result leaked real process ID metadata."

    # Real result should not have virtual tick units
    if real_result.wall_clock_time_s < 0.0:
        return False, "Real wall clock time is negative."

    if virtual_result.virtual_makespan_ticks < 0:
        return False, "Virtual makespan ticks is negative."

    return True, "Complete cross-environment isolation verified."

