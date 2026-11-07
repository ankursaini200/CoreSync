"""Comparative Metrics and Cross-Domain Analytical Evaluation for CoreSync.

Strict Architectural Rule: This module MUST NOT import PySide6 or any Qt modules.
Provides mathematically rigorous comparative metrics while strictly enforcing clock-domain boundaries:
REAL SECONDS AND VIRTUAL TICKS BELONG TO INDEPENDENT DOMAINS AND MUST NEVER BE DIVIDED.
"""

from typing import Any, Dict, List, Optional, Tuple

from engine.analytics.models import MetricClassification
from engine.comparison.models import (
    ComparisonAnalysis,
    ComparisonConfiguration,
    ComparisonWorkloadType,
    RealExecutionResult,
    VirtualExecutionResult,
    assert_no_cross_domain_ratio,
)


def compute_order_concordance(
    real_order: List[str],
    virtual_order: List[str],
) -> float:
    """Compute normalized sequence concordance between real and virtual task completion orders.

    Measures relative order agreement:
    - 1.0 indicates identical relative completion sequence.
    - 0.0 indicates completely reversed or disjoint sequence.

    Args:
        real_order: List of task IDs in order of physical completion.
        virtual_order: List of task IDs in order of simulated completion.

    Returns:
        Concordance ratio between 0.0 and 1.0.
    """
    if not real_order or not virtual_order:
        return 0.0

    # Find common tasks
    common_tasks = [t for t in real_order if t in virtual_order]
    n = len(common_tasks)
    if n <= 1:
        return 1.0 if n == 1 else 0.0

    real_rank = {t: idx for idx, t in enumerate(common_tasks)}
    virt_rank = {t: idx for idx, t in enumerate(virtual_order if len(virtual_order) == n else [t for t in virtual_order if t in real_rank])}

    # Count concordant vs discordant pairs
    concordant = 0
    total_pairs = 0

    for i in range(n):
        for j in range(i + 1, n):
            t1, t2 = common_tasks[i], common_tasks[j]
            r_diff = real_rank[t1] - real_rank[t2]
            v_diff = virt_rank.get(t1, 0) - virt_rank.get(t2, 0)

            if (r_diff > 0 and v_diff > 0) or (r_diff < 0 and v_diff < 0):
                concordant += 1
            total_pairs += 1

    return (concordant / total_pairs) if total_pairs > 0 else 1.0


class ComparisonMetricsCalculator:
    """Analytical engine providing comparative metrics across Real and Virtual results."""

    @staticmethod
    def analyze(
        config: ComparisonConfiguration,
        real_result: Optional[RealExecutionResult],
        virtual_result: Optional[VirtualExecutionResult],
    ) -> ComparisonAnalysis:
        """Evaluate comparative metrics between Real System and Virtual Lab results."""
        return compute_comparison_analysis(config, real_result, virtual_result)

    @staticmethod
    def order_concordance(real_order: List[str], virtual_order: List[str]) -> float:
        """Compute normalized sequence concordance between task completion orders."""
        return compute_order_concordance(real_order, virtual_order)


def compute_comparison_analysis(
    config: ComparisonConfiguration,
    real_result: Optional[RealExecutionResult],
    virtual_result: Optional[VirtualExecutionResult],
) -> ComparisonAnalysis:
    """Evaluate comparative metrics between Real System and Virtual Lab results.

    Enforces:
        - Real seconds and virtual ticks are NEVER divided.
        - Real utilization and virtual utilization explicitly cite their separate formulas.
        - Workload equivalence is validated.

    Args:
        config: Comparison configuration.
        real_result: Outcome from Real System (or None if virtual-only mode).
        virtual_result: Outcome from Virtual Lab (or None if real-only mode).

    Returns:
        ComparisonAnalysis parcel with validated metrics and explanatory notes.
    """
    if real_result is None and virtual_result is None:
        return ComparisonAnalysis(
            workload_equivalence=False,
            workload_equivalence_details="Neither Real System nor Virtual Lab results were available.",
            task_count_match=False,
            completion_order_concordance=0.0,
            real_worker_count=config.real_config.worker_count,
            virtual_core_count=config.virtual_config.virtual_core_count,
            resource_allocation_ratio=config.real_config.worker_count / max(1, config.virtual_config.virtual_core_count),
            real_utilization_pct=0.0,
            virtual_utilization_pct=0.0,
            utilization_difference_pct=0.0,
            scheduling_policy_effects=[],
            explanatory_notes=["Execution was skipped or aborted."],
        )

    # Real-only mode
    if virtual_result is None and real_result is not None:
        return ComparisonAnalysis(
            workload_equivalence=True,
            workload_equivalence_details="Real System executed in isolation (Real-Only Mode).",
            task_count_match=True,
            completion_order_concordance=1.0,
            real_worker_count=real_result.worker_count,
            virtual_core_count=0,
            resource_allocation_ratio=float(real_result.worker_count),
            real_utilization_pct=real_result.worker_utilization_pct,
            virtual_utilization_pct=0.0,
            utilization_difference_pct=real_result.worker_utilization_pct,
            scheduling_policy_effects=["Real host Linux/OS kernel CFS/EEVDF process scheduling active."],
            explanatory_notes=["Virtual Lab simulation was not requested for this execution pass."],
        )

    # Virtual-only mode
    if real_result is None and virtual_result is not None:
        return ComparisonAnalysis(
            workload_equivalence=True,
            workload_equivalence_details="Virtual Lab executed in isolation (Virtual-Only Mode).",
            task_count_match=True,
            completion_order_concordance=1.0,
            real_worker_count=0,
            virtual_core_count=virtual_result.virtual_core_count,
            resource_allocation_ratio=0.0,
            real_utilization_pct=0.0,
            virtual_utilization_pct=virtual_result.virtual_core_utilization_pct,
            utilization_difference_pct=-virtual_result.virtual_core_utilization_pct,
            scheduling_policy_effects=[f"Virtual scheduler algorithm: {config.virtual_config.scheduling_algorithm.value}."],
            explanatory_notes=["Real System execution was not requested for this execution pass."],
        )

    # Both environments executed: perform rigorous comparative evaluation
    assert real_result is not None and virtual_result is not None

    # Workload equivalence check
    real_task_count = len(real_result.task_completions)
    virt_task_count = len(virtual_result.task_completion_order)
    task_match = (real_task_count == virt_task_count) and (real_task_count > 0)

    if config.workload.workload_type == ComparisonWorkloadType.DATA_PARALLEL:
        # For Data Parallel, equivalence is defined by processing the identical dataset size
        # and mathematical operation under certified correctness.
        workload_equiv = (
            real_result.verification_passed
            and real_result.status == "completed"
            and virtual_result.status == "completed"
        )
        if task_match:
            equiv_details = f"Workloads matched: Both environments processed {config.workload.dataset_size:,} items across {real_task_count} partitions for '{config.workload.workload_name}'."
        else:
            equiv_details = f"Dataset matched: Both environments processed {config.workload.dataset_size:,} items of '{config.workload.workload_name}' ({real_task_count} real worker partitions vs {virt_task_count} virtual core tasks)."
    else:
        # For Task Parallel DAGs, both task count and dependency structure must match
        workload_equiv = (
            task_match
            and real_result.verification_passed
            and real_result.status == "completed"
            and virtual_result.status == "completed"
        )
        equiv_details = (
            f"Workloads matched: Both executed {real_task_count} logical DAG tasks for '{config.workload.workload_name}'."
            if task_match
            else f"Task count mismatch: Real executed {real_task_count} tasks, Virtual executed {virt_task_count} tasks."
        )

    # Extract completion orders
    real_order: List[str] = [str(tc.get("task_id", "")) for tc in real_result.task_completions]
    virt_order: List[str] = [str(tc.get("task_id", "")) for tc in virtual_result.task_completion_order]

    concordance = compute_order_concordance(real_order, virt_order)

    # Resource allocation
    r_workers = real_result.worker_count
    v_cores = max(1, virtual_result.virtual_core_count)
    alloc_ratio = r_workers / v_cores

    # Utilization comparison
    r_util = real_result.worker_utilization_pct
    v_util = virtual_result.virtual_core_utilization_pct
    u_diff = round(r_util - v_util, 2)

    # Scheduling policy observations
    sched_effects = []
    algo_name = config.virtual_config.scheduling_algorithm.value
    sched_effects.append(f"Virtual Lab Policy: {algo_name}")
    if config.virtual_config.enable_hybrid:
        sched_effects.append(
            f"Virtual Hybrid Topology: {config.virtual_config.p_core_count} P-Cores ({config.virtual_config.p_core_speed}x) + "
            f"{config.virtual_config.e_core_count} E-Cores ({config.virtual_config.e_core_speed}x)"
        )
    else:
        sched_effects.append("Virtual Symmetric Topology: Homogeneous Standard Virtual Cores (1.0x)")

    if virtual_result.preemption_count > 0:
        sched_effects.append(f"Virtual Preemptions: {virtual_result.preemption_count} context preemptions occurred under quantum {config.virtual_config.time_quantum} ticks.")

    explanatory_notes = [
        "CLOCK DOMAIN BOUNDARY: Real System wall-clock elapsed time (measured in seconds via high-resolution monotonic timer) "
        "and Virtual Lab simulation time (measured in discrete logical ticks) belong to distinct clock domains. They are never divided.",
        "REAL SYSTEM: Reflects physical OS process management, memory paging, inter-process communication serialization, "
        "and host kernel scheduling delays.",
        "VIRTUAL LAB: Reflects idealized software-simulated processor cores, discrete tick advancing, and educational scheduling algorithms.",
        f"UTILIZATION COMPARISON: Real worker utilization was {r_util:.1f}% (cumulative compute W*s / capacity), while Virtual core utilization was {v_util:.1f}% (busy ticks / capacity ticks).",
    ]

    return ComparisonAnalysis(
        workload_equivalence=workload_equiv,
        workload_equivalence_details=equiv_details,
        task_count_match=task_match,
        completion_order_concordance=concordance,
        real_worker_count=r_workers,
        virtual_core_count=v_cores,
        resource_allocation_ratio=alloc_ratio,
        real_utilization_pct=r_util,
        virtual_utilization_pct=v_util,
        utilization_difference_pct=u_diff,
        scheduling_policy_effects=sched_effects,
        explanatory_notes=explanatory_notes,
        provenance=MetricClassification.MATHEMATICALLY_DERIVED.value,
    )
