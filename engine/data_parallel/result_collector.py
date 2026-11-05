"""Result Collection and Reduction Subsystem for Data Parallelism.

Reassembles disjoint worker outputs into unified results:
- Concatenation / direct slicing for element-wise array transforms.
- Reduction aggregation (summation) for scalar reduction workloads.
"""

from typing import Any, Dict, List, Sequence, Tuple
import time
import numpy as np

from engine.data_parallel.partitioner import Chunk
from engine.data_parallel.worker import WorkerResult


class ResultCollector:
    """Collects and aggregates parallel chunk execution outputs."""

    @staticmethod
    def merge_results(
        results: Sequence[WorkerResult],
        chunks: Sequence[Chunk],
        is_reduction: bool,
    ) -> Tuple[Any, float]:
        """Aggregate chunk outputs into a final unified result.

        Args:
            results: List of WorkerResult instances from child processes.
            chunks: The original list of Chunks corresponding to partitions.
            is_reduction: If True, sums scalar chunk results. If False, reassembles array.

        Returns:
            Tuple of (merged_result, merge_time_seconds).

        Raises:
            ValueError: If results are missing chunks or any worker returned an error.
        """
        t_start = time.perf_counter()

        if not results and not chunks:
            return None, 0.0

        if len(results) != len(chunks):
            raise ValueError(f"Incomplete results: received {len(results)} outputs for {len(chunks)} chunks.")

        # Check for any worker errors
        for r in results:
            if not r.success:
                raise RuntimeError(f"Worker {r.worker_id} failed on chunk {r.chunk_id}: {r.error_message}")

        # Index results by chunk_id
        chunk_map: Dict[int, WorkerResult] = {r.chunk_id: r for r in results}
        if len(chunk_map) != len(chunks):
            raise ValueError("Duplicate chunk IDs detected in worker results.")

        for chunk in chunks:
            if chunk.chunk_id not in chunk_map:
                raise ValueError(f"Missing result for chunk {chunk.chunk_id}")

        if is_reduction:
            # Scalar aggregation (sum across all chunk results)
            total = sum(chunk_map[chunk.chunk_id].data for chunk in chunks)
            t_merge = time.perf_counter() - t_start
            return total, t_merge

        else:
            # Array reassembly in chunk order
            ordered_arrays = [chunk_map[chunk.chunk_id].data for chunk in chunks]

            if not ordered_arrays:
                return np.array([]), 0.0

            # Use np.concatenate for contiguous reassembly
            merged = np.concatenate(ordered_arrays, axis=0)
            t_merge = time.perf_counter() - t_start
            return merged, t_merge

