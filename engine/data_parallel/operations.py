"""CPU-Bound Computational Workload Kernels for Data Parallelism.

Implements genuine CPU-bound operations across five distinct classes:
1. Element-wise Transcendental Transformations
2. Polynomial Vector Arithmetic
3. Matrix Row-Vector Inner Products & Norms
4. Prime Number Sieve & Integer Factoring
5. Non-Linear Numerical Reduction / Aggregation
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Tuple
import math
import numpy as np


@dataclass(frozen=True)
class OperationSpec:
    """Metadata specification for a data-parallel operation kernel."""
    op_id: str
    name: str
    category: str
    description: str
    is_reduction: bool  # True: reduces to scalar, False: produces element-wise array
    default_dataset_size: int
    size_label: str


def _kernel_transcendental(data: np.ndarray, iterations: int = 3) -> np.ndarray:
    """Perform chained transcendental element-wise transformations on a 1D float array."""
    x = data
    # Multi-pass nonlinear transformations to ensure substantial CPU cycles per element
    result = np.zeros_like(x)
    for _ in range(iterations):
        t1 = np.sin(x) ** 2 + np.cos(x) ** 2
        t2 = np.sqrt(np.abs(x)) * np.exp(-0.00005 * np.abs(x))
        t3 = np.log1p(np.abs(x)) * np.tanh(0.005 * x)
        result = t1 + t2 + t3
        x = result * 0.5 + 0.1
    return result


def _kernel_polynomial(data: np.ndarray, passes: int = 4) -> np.ndarray:
    """Evaluate 8th-order Horner polynomial and power series expansion."""
    coeffs = [3.14159, -2.71828, 1.41421, -0.57721, 2.30258, -0.69315, 1.61803, -0.91596, 4.2]
    x = data
    y = np.zeros_like(x)
    for _ in range(passes):
        # Horner's method: (((... + c2)x + c1)x + c0)
        res = np.full_like(x, coeffs[0])
        for c in coeffs[1:]:
            res = res * (0.01 * x) + c
        y = y + res
        x = x * 0.99
    return y


def _kernel_matrix_row_norms(matrix: np.ndarray) -> np.ndarray:
    """Compute Euclidean L2 norm and weighted dot products across matrix rows."""
    # matrix is 2D shape (N, D)
    squared = np.square(matrix)
    row_sums = np.sum(squared, axis=1)
    norms = np.sqrt(row_sums)
    # Add nonlinear row-wise cross-term
    cross_terms = np.mean(np.sin(matrix), axis=1)
    return norms + cross_terms


def _is_prime_trial_division(n: int) -> bool:
    """Trial division check using 6k +/- 1 optimization."""
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    w = 2
    while i * i <= n:
        if n % i == 0:
            return False
        i += w
        w = 6 - w
    return True


def _kernel_prime_count(range_tuple: Tuple[int, int]) -> int:
    """Count primes in an integer range [start, end) via CPU-bound trial division."""
    start_val, end_val = range_tuple
    count = 0
    for num in range(start_val, end_val):
        if _is_prime_trial_division(num):
            count += 1
    return count


def _kernel_sum_of_squares(data: np.ndarray) -> float:
    """Compute nonlinear reduction sum: sum(x^2 + sin(x) * cos(x))."""
    # CPU-bound reduction
    squared = np.square(data)
    trig = np.sin(data) * np.cos(data)
    combined = squared + trig
    return float(np.sum(combined))


OPERATIONS: Dict[str, OperationSpec] = {
    "transcendental": OperationSpec(
        op_id="transcendental",
        name="Element-Wise Transcendental Math",
        category="Transform",
        description="Chained trigonometric, exponential, square root, and hyperbolic tangent operations.",
        is_reduction=False,
        default_dataset_size=1_000_000,
        size_label="Elements",
    ),
    "polynomial": OperationSpec(
        op_id="polynomial",
        name="8th-Order Horner Polynomial Evaluation",
        category="Vector Arithmetic",
        description="High-degree Horner power expansion and coefficient series evaluation.",
        is_reduction=False,
        default_dataset_size=1_500_000,
        size_label="Elements",
    ),
    "matrix_norms": OperationSpec(
        op_id="matrix_norms",
        name="Matrix Row Norms & Dot Products",
        category="Linear Algebra",
        description="Euclidean L2 vector norms and nonlinear cross terms across multi-dimensional matrix rows.",
        is_reduction=False,
        default_dataset_size=50_000,  # 50,000 rows x 64 cols
        size_label="Rows (64 cols)",
    ),
    "prime_count": OperationSpec(
        op_id="prime_count",
        name="Prime Number Calculation (Trial Division)",
        category="Integer Number Theory",
        description="Prime verification and counting across numerical sub-ranges using trial division.",
        is_reduction=True,
        default_dataset_size=250_000,
        size_label="Integer Range",
    ),
    "sum_of_squares": OperationSpec(
        op_id="sum_of_squares",
        name="Non-Linear Sum of Squares Reduction",
        category="Numerical Reduction",
        description="Parallel numerical aggregation summing nonlinear quadratic and trigonometric terms.",
        is_reduction=True,
        default_dataset_size=2_000_000,
        size_label="Elements",
    ),
}


def get_supported_operations() -> Dict[str, OperationSpec]:
    """Retrieve all available data-parallel operations."""
    return OPERATIONS


def generate_dataset(op_id: str, size: int, seed: int = 42) -> Any:
    """Generate reproducible input data tailored to the specified operation."""
    rng = np.random.RandomState(seed)

    if op_id == "transcendental":
        # Uniform float64 in [-50.0, 50.0]
        return rng.uniform(-50.0, 50.0, size=size).astype(np.float64)

    elif op_id == "polynomial":
        # Uniform float64 in [-10.0, 10.0]
        return rng.uniform(-10.0, 10.0, size=size).astype(np.float64)

    elif op_id == "matrix_norms":
        # 2D matrix (size rows, 64 columns)
        cols = 64
        return rng.randn(size, cols).astype(np.float64)

    elif op_id == "prime_count":
        # Base start offset (e.g. 100,000 to size + 100,000) for interesting prime density
        base_offset = 100_000
        return (base_offset, base_offset + size)

    elif op_id == "sum_of_squares":
        # Standard normal random floats
        return rng.randn(size).astype(np.float64)

    else:
        raise ValueError(f"Unknown operation ID: '{op_id}'")


def execute_chunk(op_id: str, data_chunk: Any, extra_args: dict = None) -> Any:
    """Execute computation kernel on a single data chunk."""
    extra_args = extra_args or {}

    if op_id == "transcendental":
        iterations = extra_args.get("iterations", 3)
        return _kernel_transcendental(data_chunk, iterations=iterations)

    elif op_id == "polynomial":
        passes = extra_args.get("passes", 4)
        return _kernel_polynomial(data_chunk, passes=passes)

    elif op_id == "matrix_norms":
        return _kernel_matrix_row_norms(data_chunk)

    elif op_id == "prime_count":
        return _kernel_prime_count(data_chunk)

    elif op_id == "sum_of_squares":
        return _kernel_sum_of_squares(data_chunk)

    else:
        raise ValueError(f"Unknown operation ID: '{op_id}'")

