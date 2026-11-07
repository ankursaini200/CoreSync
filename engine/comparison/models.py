"""Core Data Models and Serialization for Real System vs Virtual Lab Comparison.

Strict Architectural Rule: This module MUST NOT import PySide6 or any Qt modules.
Maintains strict separation between the real physical host time domain (monotonic seconds)
and the educational Virtual Lab time domain (discrete logical clock ticks).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from engine.analytics.models import MetricClassification
from engine.virtual_lab.virtual_cpu import VirtualCPUConfig
from engine.virtual_lab.virtual_scheduler import SchedulingAlgorithm


class ComparisonExecutionMode(str, Enum):
    """Execution mode selection for the comparison workstation."""
    REAL_ONLY = "real_only"
    VIRTUAL_ONLY = "virtual_only"
    COMPARE_BOTH = "compare_both"

    @property
    def display_name(self) -> str:
        names = {
            ComparisonExecutionMode.REAL_ONLY: "Real System Only",
            ComparisonExecutionMode.VIRTUAL_ONLY: "Virtual Lab Only",
            ComparisonExecutionMode.COMPARE_BOTH: "Compare Both Environments",
        }
        return names.get(self, self.value)


class ComparisonWorkloadType(str, Enum):
    """Categorization of supported comparative workloads."""
    DATA_PARALLEL = "data_parallel"
    TASK_PARALLEL = "task_parallel"

    @property
    def display_name(self) -> str:
        names = {
            ComparisonWorkloadType.DATA_PARALLEL: "Data Parallelism (SIMD / Chunks)",
            ComparisonWorkloadType.TASK_PARALLEL: "Task Parallelism (DAG Dependencies)",
        }
        return names.get(self, self.value)


@dataclass
class ComparisonWorkloadConfig:
    """Logical workload definition to be mapped into both execution environments."""
    workload_type: ComparisonWorkloadType
    workload_id: str
    workload_name: str
    dataset_size: int = 10_000
    task_count: int = 4
    extra_params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workload_type": self.workload_type.value,
            "workload_id": self.workload_id,
            "workload_name": self.workload_name,
            "dataset_size": self.dataset_size,
            "task_count": self.task_count,
            "extra_params": self.extra_params,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComparisonWorkloadConfig":
        return cls(
            workload_type=ComparisonWorkloadType(data["workload_type"]),
            workload_id=data["workload_id"],
            workload_name=data["workload_name"],
            dataset_size=data.get("dataset_size", 10_000),
            task_count=data.get("task_count", 4),
            extra_params=data.get("extra_params", {}),
        )


@dataclass
class RealSystemConfig:
    """Execution parameters for Environment A: Real System."""
    worker_count: int = 4
    pinned_cpus: Optional[List[int]] = None
    timeout_s: float = 30.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "worker_count": self.worker_count,
            "pinned_cpus": self.pinned_cpus,
            "timeout_s": self.timeout_s,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RealSystemConfig":
        return cls(
            worker_count=data.get("worker_count", 4),
            pinned_cpus=data.get("pinned_cpus"),
            timeout_s=data.get("timeout_s", 30.0),
        )


@dataclass
class VirtualLabConfig:
    """Execution parameters for Environment B: Virtual Lab."""
    virtual_core_count: int = 8
    enable_hybrid: bool = False
    p_core_count: int = 4
    e_core_count: int = 4
    p_core_speed: float = 1.5
    e_core_speed: float = 0.8
    standard_speed: float = 1.0
    scheduling_algorithm: SchedulingAlgorithm = SchedulingAlgorithm.FCFS
    time_quantum: int = 20
    max_simulation_ticks: int = 50_000

    def to_virtual_cpu_config(self) -> VirtualCPUConfig:
        return VirtualCPUConfig(
            name=f"Virtual CoreSync-{self.virtual_core_count}",
            physical_cores=self.virtual_core_count,
            logical_threads=self.virtual_core_count,
            enable_hybrid=self.enable_hybrid,
            p_core_count=self.p_core_count,
            e_core_count=self.e_core_count,
            p_core_speed=self.p_core_speed,
            e_core_speed=self.e_core_speed,
            standard_speed=self.standard_speed,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "virtual_core_count": self.virtual_core_count,
            "enable_hybrid": self.enable_hybrid,
            "p_core_count": self.p_core_count,
            "e_core_count": self.e_core_count,
            "p_core_speed": self.p_core_speed,
            "e_core_speed": self.e_core_speed,
            "standard_speed": self.standard_speed,
            "scheduling_algorithm": self.scheduling_algorithm.name,
            "time_quantum": self.time_quantum,
            "max_simulation_ticks": self.max_simulation_ticks,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VirtualLabConfig":
        algo_name = data.get("scheduling_algorithm", "FCFS")
        try:
            algo = SchedulingAlgorithm[algo_name]
        except KeyError:
            algo = SchedulingAlgorithm.FCFS
        return cls(
            virtual_core_count=data.get("virtual_core_count", 8),
            enable_hybrid=data.get("enable_hybrid", False),
            p_core_count=data.get("p_core_count", 4),
            e_core_count=data.get("e_core_count", 4),
            p_core_speed=data.get("p_core_speed", 1.5),
            e_core_speed=data.get("e_core_speed", 0.8),
            standard_speed=data.get("standard_speed", 1.0),
            scheduling_algorithm=algo,
            time_quantum=data.get("time_quantum", 20),
            max_simulation_ticks=data.get("max_simulation_ticks", 50_000),
        )


@dataclass
class ComparisonConfiguration:
    """Unified configuration for a Real vs Virtual comparison session."""
    comparison_id: str
    execution_mode: ComparisonExecutionMode
    workload: ComparisonWorkloadConfig
    real_config: RealSystemConfig
    virtual_config: VirtualLabConfig

    def to_dict(self) -> Dict[str, Any]:
        return {
            "comparison_id": self.comparison_id,
            "execution_mode": self.execution_mode.value,
            "workload": self.workload.to_dict(),
            "real_config": self.real_config.to_dict(),
            "virtual_config": self.virtual_config.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComparisonConfiguration":
        return cls(
            comparison_id=data["comparison_id"],
            execution_mode=ComparisonExecutionMode(data["execution_mode"]),
            workload=ComparisonWorkloadConfig.from_dict(data["workload"]),
            real_config=RealSystemConfig.from_dict(data["real_config"]),
            virtual_config=VirtualLabConfig.from_dict(data["virtual_config"]),
        )


@dataclass
class RealExecutionResult:
    """Empirical telemetry captured from Environment A: Real System."""
    status: str  # "completed", "failed", "cancelled", "skipped"
    wall_clock_time_s: float
    worker_count: int
    worker_intervals: List[Tuple[float, float]] = field(default_factory=list)
    aggregate_worker_compute_time_s: float = 0.0
    compute_interval_union_s: float = 0.0
    no_worker_compute_time_s: float = 0.0
    sequential_baseline_s: Optional[float] = None
    actual_speedup: Optional[float] = None
    worker_utilization_pct: float = 0.0
    peak_memory_rss_mb: float = 0.0
    host_cpu_percent: float = 0.0
    task_completions: List[Dict[str, Any]] = field(default_factory=list)
    verification_passed: bool = True
    error_message: Optional[str] = None
    provenance: str = MetricClassification.DIRECTLY_MEASURED.value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "wall_clock_time_s": round(self.wall_clock_time_s, 6),
            "worker_count": self.worker_count,
            "worker_intervals": [(round(s, 6), round(e, 6)) for s, e in self.worker_intervals],
            "aggregate_worker_compute_time_s": round(self.aggregate_worker_compute_time_s, 6),
            "compute_interval_union_s": round(self.compute_interval_union_s, 6),
            "no_worker_compute_time_s": round(self.no_worker_compute_time_s, 6),
            "sequential_baseline_s": round(self.sequential_baseline_s, 6) if self.sequential_baseline_s is not None else None,
            "actual_speedup": round(self.actual_speedup, 4) if self.actual_speedup is not None else None,
            "worker_utilization_pct": round(self.worker_utilization_pct, 2),
            "peak_memory_rss_mb": round(self.peak_memory_rss_mb, 2),
            "host_cpu_percent": round(self.host_cpu_percent, 2),
            "task_completions": self.task_completions,
            "verification_passed": self.verification_passed,
            "error_message": self.error_message,
            "provenance": self.provenance,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RealExecutionResult":
        raw_intervals = data.get("worker_intervals", [])
        parsed_intervals = [(float(s), float(e)) for s, e in raw_intervals]
        return cls(
            status=data.get("status", "completed"),
            wall_clock_time_s=data.get("wall_clock_time_s", 0.0),
            worker_count=data.get("worker_count", 1),
            worker_intervals=parsed_intervals,
            aggregate_worker_compute_time_s=data.get("aggregate_worker_compute_time_s", 0.0),
            compute_interval_union_s=data.get("compute_interval_union_s", 0.0),
            no_worker_compute_time_s=data.get("no_worker_compute_time_s", 0.0),
            sequential_baseline_s=data.get("sequential_baseline_s"),
            actual_speedup=data.get("actual_speedup"),
            worker_utilization_pct=data.get("worker_utilization_pct", 0.0),
            peak_memory_rss_mb=data.get("peak_memory_rss_mb", 0.0),
            host_cpu_percent=data.get("host_cpu_percent", 0.0),
            task_completions=data.get("task_completions", []),
            verification_passed=data.get("verification_passed", True),
            error_message=data.get("error_message"),
            provenance=data.get("provenance", MetricClassification.DIRECTLY_MEASURED.value),
        )


@dataclass
class VirtualExecutionResult:
    """Simulation outcomes captured from Environment B: Virtual Lab."""
    status: str  # "completed", "failed", "cancelled", "skipped"
    virtual_makespan_ticks: int
    simulated_clock_ticks: int
    virtual_core_utilization_pct: float
    virtual_core_count: int
    virtual_core_allocation: Dict[int, List[str]] = field(default_factory=dict)
    task_completion_order: List[Dict[str, Any]] = field(default_factory=list)
    scheduling_events: List[Dict[str, Any]] = field(default_factory=list)
    simulated_throughput_tasks_per_tick: float = 0.0
    avg_waiting_ticks: float = 0.0
    avg_turnaround_ticks: float = 0.0
    preemption_count: int = 0
    error_message: Optional[str] = None
    provenance: str = MetricClassification.SIMULATED_VIRTUAL.value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "virtual_makespan_ticks": self.virtual_makespan_ticks,
            "simulated_clock_ticks": self.simulated_clock_ticks,
            "virtual_core_utilization_pct": round(self.virtual_core_utilization_pct, 2),
            "virtual_core_count": self.virtual_core_count,
            "virtual_core_allocation": {str(k): v for k, v in self.virtual_core_allocation.items()},
            "task_completion_order": self.task_completion_order,
            "scheduling_events": self.scheduling_events,
            "simulated_throughput_tasks_per_tick": round(self.simulated_throughput_tasks_per_tick, 6),
            "avg_waiting_ticks": round(self.avg_waiting_ticks, 2),
            "avg_turnaround_ticks": round(self.avg_turnaround_ticks, 2),
            "preemption_count": self.preemption_count,
            "error_message": self.error_message,
            "provenance": self.provenance,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VirtualExecutionResult":
        raw_alloc = data.get("virtual_core_allocation", {})
        alloc = {int(k): v for k, v in raw_alloc.items()}
        return cls(
            status=data.get("status", "completed"),
            virtual_makespan_ticks=data.get("virtual_makespan_ticks", 0),
            simulated_clock_ticks=data.get("simulated_clock_ticks", 0),
            virtual_core_utilization_pct=data.get("virtual_core_utilization_pct", 0.0),
            virtual_core_count=data.get("virtual_core_count", 1),
            virtual_core_allocation=alloc,
            task_completion_order=data.get("task_completion_order", []),
            scheduling_events=data.get("scheduling_events", []),
            simulated_throughput_tasks_per_tick=data.get("simulated_throughput_tasks_per_tick", 0.0),
            avg_waiting_ticks=data.get("avg_waiting_ticks", 0.0),
            avg_turnaround_ticks=data.get("avg_turnaround_ticks", 0.0),
            preemption_count=data.get("preemption_count", 0),
            error_message=data.get("error_message"),
            provenance=data.get("provenance", MetricClassification.SIMULATED_VIRTUAL.value),
        )


@dataclass
class ComparisonAnalysis:
    """Mathematically valid comparative evaluation between Real System and Virtual Lab."""
    workload_equivalence: bool
    workload_equivalence_details: str
    task_count_match: bool
    completion_order_concordance: float  # Rank correlation or order matching ratio (0.0 to 1.0)
    real_worker_count: int
    virtual_core_count: int
    resource_allocation_ratio: float  # real_workers / virtual_cores
    real_utilization_pct: float  # Cumulative compute / capacity
    virtual_utilization_pct: float  # Core busy ticks / capacity ticks
    utilization_difference_pct: float  # Real util - Virtual util
    scheduling_policy_effects: List[str] = field(default_factory=list)
    explanatory_notes: List[str] = field(default_factory=list)
    provenance: str = MetricClassification.MATHEMATICALLY_DERIVED.value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workload_equivalence": self.workload_equivalence,
            "workload_equivalence_details": self.workload_equivalence_details,
            "task_count_match": self.task_count_match,
            "completion_order_concordance": round(self.completion_order_concordance, 4),
            "real_worker_count": self.real_worker_count,
            "virtual_core_count": self.virtual_core_count,
            "resource_allocation_ratio": round(self.resource_allocation_ratio, 4),
            "real_utilization_pct": round(self.real_utilization_pct, 2),
            "virtual_utilization_pct": round(self.virtual_utilization_pct, 2),
            "utilization_difference_pct": round(self.utilization_difference_pct, 2),
            "scheduling_policy_effects": self.scheduling_policy_effects,
            "explanatory_notes": self.explanatory_notes,
            "provenance": self.provenance,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComparisonAnalysis":
        return cls(
            workload_equivalence=data.get("workload_equivalence", False),
            workload_equivalence_details=data.get("workload_equivalence_details", ""),
            task_count_match=data.get("task_count_match", False),
            completion_order_concordance=data.get("completion_order_concordance", 0.0),
            real_worker_count=data.get("real_worker_count", 1),
            virtual_core_count=data.get("virtual_core_count", 1),
            resource_allocation_ratio=data.get("resource_allocation_ratio", 1.0),
            real_utilization_pct=data.get("real_utilization_pct", 0.0),
            virtual_utilization_pct=data.get("virtual_utilization_pct", 0.0),
            utilization_difference_pct=data.get("utilization_difference_pct", 0.0),
            scheduling_policy_effects=data.get("scheduling_policy_effects", []),
            explanatory_notes=data.get("explanatory_notes", []),
            provenance=data.get("provenance", MetricClassification.MATHEMATICALLY_DERIVED.value),
        )


@dataclass
class ComparisonSessionResult:
    """Self-contained archival record of a complete Real vs Virtual comparison execution."""
    comparison_id: str
    timestamp: str
    configuration: ComparisonConfiguration
    real_result: Optional[RealExecutionResult] = None
    virtual_result: Optional[VirtualExecutionResult] = None
    analysis: Optional[ComparisonAnalysis] = None
    hardware_metadata: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    cancelled: bool = False
    error_message: Optional[str] = None
    session_type: str = "real_vs_virtual_comparison"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "comparison_id": self.comparison_id,
            "timestamp": self.timestamp,
            "session_type": self.session_type,
            "configuration": self.configuration.to_dict(),
            "real_result": self.real_result.to_dict() if self.real_result else None,
            "virtual_result": self.virtual_result.to_dict() if self.virtual_result else None,
            "analysis": self.analysis.to_dict() if self.analysis else None,
            "hardware_metadata": self.hardware_metadata,
            "success": self.success,
            "cancelled": self.cancelled,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComparisonSessionResult":
        cfg = ComparisonConfiguration.from_dict(data["configuration"])
        real_res = RealExecutionResult.from_dict(data["real_result"]) if data.get("real_result") else None
        virt_res = VirtualExecutionResult.from_dict(data["virtual_result"]) if data.get("virtual_result") else None
        analysis = ComparisonAnalysis.from_dict(data["analysis"]) if data.get("analysis") else None
        return cls(
            comparison_id=data.get("comparison_id", cfg.comparison_id),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            configuration=cfg,
            real_result=real_res,
            virtual_result=virt_res,
            analysis=analysis,
            hardware_metadata=data.get("hardware_metadata", {}),
            success=data.get("success", True),
            cancelled=data.get("cancelled", False),
            error_message=data.get("error_message"),
            session_type=data.get("session_type", "real_vs_virtual_comparison"),
        )


def assert_no_cross_domain_ratio(real_val: float, virtual_val: float) -> None:
    """Enforce the critical measurement rule: real seconds and virtual ticks must never be divided.

    Raises:
        ValueError: If an attempt is made to compute an invalid cross-domain ratio.
    """
    raise ValueError(
        "Invalid Cross-Domain Operation: Dividing real physical elapsed wall-clock seconds by "
        "discrete virtual logical clock ticks violates CoreSync measurement integrity. "
        "Real System and Virtual Lab operate in fundamentally distinct clock domains."
    )

