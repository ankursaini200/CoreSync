"""Dataset Partitioning Subsystem for Data Parallelism.

Splits uniform datasets and index ranges into contiguous chunks for parallel worker execution.
Supports even and uneven divisions, remainder distribution, and zero-element edge cases.
"""

from dataclasses import dataclass
from typing import Any, List, Sequence, Tuple
import numpy as np


@dataclass(frozen=True)
class Chunk:
    """Specification of a contiguous dataset partition."""
    chunk_id: int
    start_idx: int
    end_idx: int
    size: int

    def __post_init__(self):
        if self.end_idx < self.start_idx:
            raise ValueError(f"Invalid chunk bounds: start_idx={self.start_idx} > end_idx={self.end_idx}")
        if self.size != (self.end_idx - self.start_idx):
            raise ValueError(f"Size mismatch: size={self.size} != end_idx - start_idx ({self.end_idx - self.start_idx})")


class DataPartitioner:
    """Divides datasets and index spaces into disjoint contiguous partitions."""

    @staticmethod
    def partition_indices(total_items: int, num_chunks: int) -> List[Chunk]:
        """Compute index ranges for partitioning total_items across num_chunks.

        Distributes remainder items fairly across the earliest chunks so that:
        - All chunks differ in size by at most 1 item.
        - Sum of chunk sizes is exactly total_items.
        - There are no gaps and no overlapping indices.

        Args:
            total_items: Total number of items in dataset (must be >= 0).
            num_chunks: Desired number of partitions (must be >= 1).

        Returns:
            List of Chunk objects covering [0, total_items).
        """
        if total_items < 0:
            raise ValueError(f"total_items cannot be negative (got {total_items})")
        if num_chunks <= 0:
            raise ValueError(f"num_chunks must be positive (got {num_chunks})")

        if total_items == 0:
            return []

        # Cap chunk count at total_items (avoid empty chunks when items < workers)
        effective_chunks = min(total_items, num_chunks)

        base_size = total_items // effective_chunks
        remainder = total_items % effective_chunks

        chunks: List[Chunk] = []
        current_start = 0

        for chunk_id in range(effective_chunks):
            # The first 'remainder' chunks receive 1 extra item
            chunk_size = base_size + (1 if chunk_id < remainder else 0)
            current_end = current_start + chunk_size

            chunks.append(Chunk(
                chunk_id=chunk_id,
                start_idx=current_start,
                end_idx=current_end,
                size=chunk_size,
            ))
            current_start = current_end

        return chunks

    @staticmethod
    def partition_array(array: np.ndarray, num_chunks: int) -> List[Tuple[Chunk, np.ndarray]]:
        """Slice a NumPy array into contiguous chunk views without copying data.

        Args:
            array: NumPy array to partition.
            num_chunks: Desired number of partitions.

        Returns:
            List of (Chunk, ndarray_slice) tuples.
        """
        total_items = len(array)
        chunks = DataPartitioner.partition_indices(total_items, num_chunks)
        return [(chunk, array[chunk.start_idx:chunk.end_idx]) for chunk in chunks]

    @staticmethod
    def verify_partitions(total_items: int, chunks: Sequence[Chunk]) -> bool:
        """Validate that chunks strictly partition [0, total_items) with zero gaps or overlaps."""
        if total_items == 0:
            return len(chunks) == 0

        if not chunks:
            return False

        if chunks[0].start_idx != 0:
            return False

        if chunks[-1].end_idx != total_items:
            return False

        covered_sum = 0
        for i, chunk in enumerate(chunks):
            if chunk.chunk_id != i:
                return False
            covered_sum += chunk.size
            if i > 0 and chunk.start_idx != chunks[i - 1].end_idx:
                return False

        return covered_sum == total_items

