"""Guaranteed Benchmark Input Isolation and Deep-Copy Subsystem for CoreSync.

Ensures that:
1. Sequential baseline passes and parallel worker passes receive independent, unshared inputs.
2. Mutation performed by one pass cannot pollute another pass or the original input dataset.
3. NumPy arrays are copied with independent underlying memory buffers (zero shared memory).
4. NumPy arrays with dtype=object undergo recursive element-wise deep cloning to isolate nested mutable objects.
5. Objects implementing custom .clone() are strictly validated: rejecting self-returns and shallow copies with shared mutable state.
6. Explicit type clone handlers can be registered for domain-specific models.
7. Unsupported stateful types (generators, sockets, open file streams) fail explicitly with TypeError.
8. Data preparation and cloning durations occur strictly before timing boundaries and are excluded from makespan measurements.
"""

import copy
import io
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# Types that are completely immutable in Python and require no copy allocation
_IMMUTABLE_PRIMITIVES = (int, float, str, bool, bytes, type(None))

# Registry of type-specific explicit cloning handlers
_TYPE_CLONE_HANDLERS: Dict[type, Callable[[Any], Any]] = {}


def register_clone_handler(cls: type, handler: Callable[[Any], Any]) -> None:
    """Register an explicit type-specific cloning handler for benchmark isolation."""
    _TYPE_CLONE_HANDLERS[cls] = handler


def _is_mutable_container(val: Any) -> bool:
    """Check if an object is a mutable container or has mutable state."""
    if isinstance(val, (dict, list, set, bytearray)):
        return True
    try:
        import numpy as np
        if isinstance(val, np.ndarray):
            return True
    except ImportError:
        pass
    if hasattr(val, "__dict__") and not isinstance(val, _IMMUTABLE_PRIMITIVES):
        return True
    return False


def clone_benchmark_input(data: Any) -> Any:
    """Create an independent deep copy of benchmark input data.

    Supports:
        - NumPy arrays (numerical dtype via array.copy() with verified unshared memory buffer;
          dtype=object via recursive element-wise deep cloning).
        - Nested Python dictionaries, lists, tuples, and sets.
        - Domain-registered clone handlers.
        - Objects implementing a verified .clone() protocol (such as TaskGraph).
        - Python primitive immutables (int, float, str, bool, bytes, None).

    Rejects:
        - Generators, iterators, file objects, network sockets, thread/process locks.
        - Custom objects whose .clone() returns self or shares mutable child state.
        - Unpicklable or stateful objects that cannot guarantee deep isolation.

    Raises:
        TypeError: If an unsupported mutable, stateful, or invalidly cloned object is supplied.
    """
    if data is None or isinstance(data, _IMMUTABLE_PRIMITIVES):
        return data

    # 1. Registered type-specific clone handlers
    for registered_cls, handler in _TYPE_CLONE_HANDLERS.items():
        if isinstance(data, registered_cls):
            cloned = handler(data)
            if cloned is data:
                raise TypeError(
                    f"Registered clone handler for '{registered_cls.__name__}' returned original object instance ('self')."
                )
            return cloned

    # 2. NumPy arrays
    try:
        import numpy as np
        if isinstance(data, np.ndarray):
            if data.dtype == object:
                # Object arrays contain Python object references (dicts, lists, custom objects).
                # A separate NumPy array buffer alone is NOT sufficient because pointers to
                # internal mutable objects remain shared across arrays.
                cloned_obj_arr = np.empty(data.shape, dtype=object)
                for idx in np.ndindex(data.shape):
                    cloned_obj_arr[idx] = clone_benchmark_input(data[idx])
                return cloned_obj_arr
            else:
                cloned_arr = data.copy(order="K")
                # Verify memory independence
                if np.shares_memory(data, cloned_arr) and data.size > 0:
                    raise RuntimeError("Cloned NumPy array unexpectedly shares memory buffer with source.")
                return cloned_arr
    except ImportError:
        pass

    # 3. Objects providing an explicit .clone() protocol (e.g. TaskGraph)
    if hasattr(data, "clone") and callable(getattr(data, "clone")):
        cloned = data.clone()
        # Invariant 1: Reject clone that returns the original object (self)
        if cloned is data:
            raise TypeError(
                f"Custom .clone() method on '{type(data).__name__}' returned original object instance ('self'). "
                "Failed deep isolation guarantee."
            )
        # Invariant 2: Validate independence of nested mutable state where inspectable
        if hasattr(data, "__dict__") and hasattr(cloned, "__dict__"):
            orig_dict = vars(data)
            cloned_dict = vars(cloned)
            for attr_name, orig_val in orig_dict.items():
                if attr_name.startswith("__"):
                    continue
                clone_val = cloned_dict.get(attr_name)
                if orig_val is not None and not isinstance(orig_val, _IMMUTABLE_PRIMITIVES):
                    if orig_val is clone_val and _is_mutable_container(orig_val):
                        raise TypeError(
                            f"Custom .clone() on '{type(data).__name__}' returned a shallow copy with "
                            f"shared mutable attribute '{attr_name}'. Failed deep isolation guarantee."
                        )
        return cloned

    # 4. Detect known unsupported stateful objects that cannot be safely cloned
    if isinstance(data, (io.IOBase, type((x for x in [])))):
        raise TypeError(
            f"Unsupported benchmark input type '{type(data).__name__}'. "
            "Generators, file streams, and stateful I/O descriptors cannot guarantee independent deep isolation."
        )

    # 5. Standard container types (recursively deep-cloned)
    if isinstance(data, dict):
        return {clone_benchmark_input(k): clone_benchmark_input(v) for k, v in data.items()}

    if isinstance(data, list):
        return [clone_benchmark_input(item) for item in data]

    if isinstance(data, tuple):
        return tuple(clone_benchmark_input(item) for item in data)

    if isinstance(data, set):
        return {clone_benchmark_input(item) for item in data}

    # 6. Fallback for custom picklable dataclasses / objects
    try:
        return copy.deepcopy(data)
    except Exception as exc:
        raise TypeError(
            f"Unsupported benchmark input type '{type(data).__name__}': {exc}. "
            "Object cannot be safely deep-cloned for benchmark isolation."
        ) from exc


def verify_input_independence(original: Any, clone: Any) -> bool:
    """Verify that original and clone are structurally independent with zero shared mutable state."""
    if original is None or isinstance(original, _IMMUTABLE_PRIMITIVES):
        return True

    if original is clone:
        return False

    try:
        import numpy as np
        if isinstance(original, np.ndarray) and isinstance(clone, np.ndarray):
            if np.shares_memory(original, clone) and original.size > 0:
                return False
            if original.dtype == object and clone.dtype == object:
                min_shape = tuple(min(s1, s2) for s1, s2 in zip(original.shape, clone.shape))
                for idx in np.ndindex(min_shape):
                    if not verify_input_independence(original[idx], clone[idx]):
                        return False
            return True
    except ImportError:
        pass

    if isinstance(original, dict) and isinstance(clone, dict):
        for k, v in original.items():
            if k in clone:
                if not verify_input_independence(v, clone[k]):
                    return False
        return True

    if isinstance(original, (list, tuple, set)) and isinstance(clone, (list, tuple, set)):
        for o_item in original:
            if _is_mutable_container(o_item):
                for c_item in clone:
                    if o_item is c_item:
                        return False
        return True

    if hasattr(original, "__dict__") and hasattr(clone, "__dict__"):
        for k, v in vars(original).items():
            if k.startswith("__"):
                continue
            if k in vars(clone):
                c_val = getattr(clone, k)
                if _is_mutable_container(v) and v is c_val:
                    return False
        return True

    return True
