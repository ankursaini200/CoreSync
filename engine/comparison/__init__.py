"""Real System vs Virtual Lab Comparison Module for CoreSync.

Provides unified comparison workstation capabilities connecting real multiprocessing
execution with software-simulated Virtual CPU and Virtual Scheduler.
"""

from engine.comparison.models import (
    ComparisonAnalysis,
    ComparisonConfiguration,
    ComparisonExecutionMode,
    ComparisonSessionResult,
    ComparisonWorkloadConfig,
    ComparisonWorkloadType,
    RealExecutionResult,
    RealSystemConfig,
    VirtualExecutionResult,
    VirtualLabConfig,
    assert_no_cross_domain_ratio,
)
from engine.comparison.workload_mapper import (
    MappedRealWorkload,
    MappedVirtualWorkload,
    WorkloadEquivalenceReport,
    get_supported_workloads,
    map_workload,
)
from engine.comparison.real_executor import RealComparisonExecutor
from engine.comparison.virtual_executor import VirtualComparisonExecutor
from engine.comparison.comparison_metrics import (
    ComparisonMetricsCalculator,
    compute_comparison_analysis,
    compute_order_concordance,
)
from engine.comparison.comparison_validator import (
    ComparisonValidationError,
    assert_valid_configuration,
    validate_comparison_configuration,
    validate_result_isolation,
)
from engine.comparison.comparison_runner import ComparisonRunner

__all__ = [
    "ComparisonAnalysis",
    "ComparisonConfiguration",
    "ComparisonExecutionMode",
    "ComparisonRunner",
    "ComparisonSessionResult",
    "ComparisonValidationError",
    "ComparisonWorkloadConfig",
    "ComparisonWorkloadType",
    "MappedRealWorkload",
    "MappedVirtualWorkload",
    "RealComparisonExecutor",
    "RealExecutionResult",
    "RealSystemConfig",
    "VirtualComparisonExecutor",
    "VirtualExecutionResult",
    "VirtualLabConfig",
    "WorkloadEquivalenceReport",
    "assert_no_cross_domain_ratio",
    "assert_valid_configuration",
    "compute_comparison_analysis",
    "compute_order_concordance",
    "get_supported_workloads",
    "map_workload",
    "validate_comparison_configuration",
    "validate_result_isolation",
]
