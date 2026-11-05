"""Data Parallelism Engine for CoreSync.

Implements chunk partitioning, isolated multiprocessing workers, result aggregation,
and empirical speedup verification.
"""

from engine.data_parallel.partitioner import Chunk, DataPartitioner
from engine.data_parallel.operations import (
    OperationSpec,
    execute_chunk,
    generate_dataset,
    get_supported_operations,
)
from engine.data_parallel.worker import WorkerResult, WorkerTask, data_parallel_worker_loop
from engine.data_parallel.result_collector import ResultCollector
from engine.data_parallel.verification import ResultVerifier, VerificationResult
from engine.data_parallel.executor import (
    DataParallelBenchmarkResult,
    DataParallelExecutor,
    ParallelExecutionResult,
    ParallelTimingBreakdown,
)

__all__ = [
    "Chunk",
    "DataPartitioner",
    "OperationSpec",
    "execute_chunk",
    "generate_dataset",
    "get_supported_operations",
    "WorkerResult",
    "WorkerTask",
    "data_parallel_worker_loop",
    "ResultCollector",
    "ResultVerifier",
    "VerificationResult",
    "DataParallelBenchmarkResult",
    "DataParallelExecutor",
    "ParallelExecutionResult",
    "ParallelTimingBreakdown",
]

