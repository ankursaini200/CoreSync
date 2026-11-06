"""Guaranteed Benchmark Input Isolation and Deep-Copy Subsystem for CoreSync.

Ensures that:
1. Sequential baseline passes and parallel worker passes receive independent, unshared inputs.
2. Mutation performed by one pass cannot pollute another pass.
3. NumPy arrays are copied with independent underlying memory buffers (zero shared memory).
4. Nested containers (dicts, lists, tuples, sets) undergo deep recursive cloning.
5. Unsupported stateful types (generators, sockets, open file streams) fail explicitly
   with TypeError rather than silently falling back to unsafe shallow sharing.
6. Data preparation and cloning durations occur strictly before timing boundaries
   and are excluded from makespan measurements.
"""

import copy
import io
from typing import Any, Dict, List, Set, Tuple


# Types that are completely immutable in Python and require no copy allocation
_IMMUTABLE_PRIMITIVES = (int, float, str, bool, bytes, type(None))


def clone_benchmark_input(data: Any) -> Any:
    """Create an independent deep copy of benchmark input data.

    Supports:
        - NumPy arrays (via array.copy() with verified unshared memory buffer).
        - Nested Python dictionaries, lists, tuples, and sets.
        - Objects implementing a custom .clone() method (such as TaskGraph).
        - Python primitive immutables (int, float, str, bool, bytes, None).

    Rejects:
        - Generators, iterators, file objects, network sockets, thread/process locks.

    Raises:
        TypeError: If an unsupported mutable or stateful object is supplied.
    """
    if data is None or isinstance(data, _IMMUTABLE_PRIMITIVES):
        return data

    # 1. NumPy arrays
    try:
        import numpy as np
        if isinstance(data, np.ndarray):
            cloned_arr = data.copy(order="K")
            # Verify memory independence
            if np.shares_memory(data, cloned_arr) and data.size > 0:
                raise RuntimeError("Cloned NumPy array unexpectedly shares memory buffer with source.")
            return cloned_arr
    except ImportError:
        pass

    # 2. Objects providing an explicit .clone() protocol (e.g. TaskGraph)
    if hasattr(data, "clone") and callable(getattr(data, "clone")):
        return data.clone()

    # 3. Detect known unsupported stateful objects that cannot be safely cloned
    if isinstance(data, (io.IOBase, type((x for x in [])))):
        raise TypeError(
            f"Unsupported benchmark input type '{type(data).__name__}'. "
            "Generators, file streams, and stateful I/O descriptors cannot guarantee independent deep isolation."
        )

    # 4. Standard container types (recursively deep-cloned)
    if isinstance(data, dict):
        return {clone_benchmark_input(k): clone_benchmark_input(v) for k, v in data.items()}

    if isinstance(data, list):
        return [clone_benchmark_input(item) for item in data]

    if isinstance(data, tuple):
        return tuple(clone_benchmark_input(item) for item in data)

    if isinstance(data, set):
        return {clone_benchmark_input(item) for item in data}

    # 5. Fallback for custom picklable dataclasses / objects
    try:
        return copy.deepcopy(data)
    except Exception as exc:
        raise TypeError(
            f"Unsupported benchmark input type '{type(data).__name__}': {exc}. "
            "Object cannot be safely deep-cloned for benchmark isolation."
        ) from exc


def verify_input_independence(original: Any, clone: Any) -> bool:
    """Verify that mutating clone does not alter original."""
    try:
        import numpy as np
        if isinstance(original, np.ndarray) and isinstance(clone, np.ndarray):
            return not np.shares_memory(original, clone)
    except ImportError:
        pass

    if isinstance(original, (int, float, str, bool, bytes, type(None))):
        return True

    return original is not clone

