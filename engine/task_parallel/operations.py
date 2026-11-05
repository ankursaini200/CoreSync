"""CPU-Bound Computational Kernels for Task Parallelism.

Strict Architectural Rule: This module MUST NOT import PySide6 or any Qt modules.
Executes genuine CPU-bound algorithms without sleep timers or mocked completions.
"""

import math
import time
from typing import Any, Dict
import numpy as np


def execute_task_kernel(task_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch and execute genuine CPU-bound computations based on task_type."""
    # Check for test-injected failure
    if params.get("fail_flag", False) or params.get("simulate_error"):
        error_msg = params.get("simulate_error") or "Simulated task execution failure"
        raise RuntimeError(error_msg)

    if task_type == "prime_calc":
        return _kernel_prime_calc(params)
    elif task_type == "matrix_mult":
        return _kernel_matrix_mult(params)
    elif task_type == "numerical_integration":
        return _kernel_numerical_integration(params)
    elif task_type == "sorting":
        return _kernel_sorting(params)
    elif task_type == "fibonacci":
        return _kernel_fibonacci(params)
    elif task_type == "data_transform":
        return _kernel_data_transform(params)
    else:
        raise ValueError(f"Unsupported task_type: '{task_type}'")


def _kernel_prime_calc(params: Dict[str, Any]) -> Dict[str, Any]:
    """Prime number calculation using trial division with 6k ± 1 optimization."""
    limit = int(params.get("limit", 100_000))
    start = int(params.get("start", 2))

    primes = []
    for n in range(max(2, start), limit + 1):
        if n in (2, 3):
            primes.append(n)
            continue
        if n % 2 == 0 or n % 3 == 0:
            continue
        is_p = True
        limit_root = int(math.isqrt(n))
        for d in range(5, limit_root + 1, 6):
            if n % d == 0 or n % (d + 2) == 0:
                is_p = False
                break
        if is_p:
            primes.append(n)

    count = len(primes)
    largest = primes[-1] if primes else 0
    checksum = float(sum(primes[-100:])) if primes else 0.0

    return {
        "count": count,
        "largest_prime": largest,
        "checksum": checksum,
        "range": [start, limit],
        "primes": primes,  # Complete prime list for full equivalence verification
    }


def _kernel_matrix_mult(params: Dict[str, Any]) -> Dict[str, Any]:
    """Square matrix multiplication and Frobenius norm calculation."""
    size = int(params.get("size", 250))
    seed = int(params.get("seed", 42))

    rng = np.random.default_rng(seed)
    A = rng.standard_normal((size, size), dtype=np.float64)
    B = rng.standard_normal((size, size), dtype=np.float64)

    # Standard matrix multiplication
    C = np.dot(A, B)
    trace = float(np.trace(C))
    frobenius_norm = float(np.linalg.norm(C))
    mean_val = float(np.mean(C))

    return {
        "matrix_shape": [size, size],
        "trace": trace,
        "frobenius_norm": frobenius_norm,
        "checksum": frobenius_norm + trace,
        "mean": mean_val,
        "matrix": C,  # Complete output matrix for element-by-element equivalence verification
    }


def _kernel_numerical_integration(params: Dict[str, Any]) -> Dict[str, Any]:
    """Composite Simpson's Rule integration of an oscillating transcendental function.

    Integral: ∫[a, b] sin(x^2) * exp(-x / 10) dx
    """
    intervals = int(params.get("intervals", 100_000))
    if intervals % 2 != 0:
        intervals += 1  # Simpson's rule requires even number of intervals
    a = float(params.get("a", 0.0))
    b = float(params.get("b", 10.0))

    x = np.linspace(a, b, intervals + 1)
    y = np.sin(x ** 2) * np.exp(-x / 10.0)

    # Simpson's coefficients: 1, 4, 2, 4, 2, ..., 4, 1
    h = (b - a) / intervals
    weights = np.ones(intervals + 1)
    weights[1:-1:2] = 4.0
    weights[2:-1:2] = 2.0

    integral = float((h / 3.0) * np.sum(weights * y))

    return {
        "integral": integral,
        "intervals": intervals,
        "bounds": [a, b],
        "checksum": abs(integral) * 1000.0,
    }


def _kernel_sorting(params: Dict[str, Any]) -> Dict[str, Any]:
    """Array generation, multi-key sorting, and strictly-sorted verification."""
    size = int(params.get("size", 200_000))
    seed = int(params.get("seed", 99))

    rng = np.random.default_rng(seed)
    arr = rng.uniform(-1000.0, 1000.0, size=size)

    # Sort array
    sorted_arr = np.sort(arr)

    # Verify monotonic ascending order
    is_sorted = bool(np.all(sorted_arr[:-1] <= sorted_arr[1:]))
    min_val = float(sorted_arr[0]) if size > 0 else 0.0
    max_val = float(sorted_arr[-1]) if size > 0 else 0.0
    median_val = float(np.median(sorted_arr)) if size > 0 else 0.0

    return {
        "size": size,
        "is_sorted": is_sorted,
        "min": min_val,
        "max": max_val,
        "median": median_val,
        "checksum": min_val + max_val + median_val,
        "sorted_array": sorted_arr,  # Complete sorted array for element-by-element equivalence verification
    }


def _kernel_fibonacci(params: Dict[str, Any]) -> Dict[str, Any]:
    """Large Fibonacci computation via fast doubling algorithm."""
    n = int(params.get("n", 25_000))

    def fib_doubling(k: int):
        if k == 0:
            return (0, 1)
        a, b = fib_doubling(k >> 1)
        c = a * ((b << 1) - a)
        d = a * a + b * b
        if k & 1:
            return (d, c + d)
        return (c, d)

    fib_n, _ = fib_doubling(n)
    # Estimate exact digit count using bit length: log10(2) approx 0.30102999566
    digit_count = int(fib_n.bit_length() * 0.3010299956639812) + 1 if fib_n > 0 else 1
    last_6_digits = int(fib_n % 1_000_000)

    return {
        "n": n,
        "digit_count": digit_count,
        "last_6_digits": last_6_digits,
        "checksum": float(last_6_digits),
        "fib_value": fib_n,  # Complete exact integer value for full mathematical equivalence
    }


def _kernel_data_transform(params: Dict[str, Any]) -> Dict[str, Any]:
    """Multi-pass transcendental transformations, polynomial Horner expansions, and moments."""
    size = int(params.get("size", 150_000))
    passes = int(params.get("passes", 3))
    seed = int(params.get("seed", 123))

    rng = np.random.default_rng(seed)
    data = rng.uniform(0.1, 10.0, size=size)

    # Multi-pass iterative transformation
    result = data.copy()
    for p in range(passes):
        result = np.sin(result) ** 2 + np.cos(result) ** 2 + np.sqrt(result)
        # Horner polynomial: 0.5 + 1.2*x - 0.03*x^2
        result = 0.5 + result * (1.2 - 0.03 * result)

    mean_val = float(np.mean(result))
    std_val = float(np.std(result))
    checksum = float(np.sum(result[-50:]))

    return {
        "size": size,
        "passes": passes,
        "mean": mean_val,
        "std": std_val,
        "checksum": checksum,
        "output_array": result,  # Complete transformed array for full array verification
    }
