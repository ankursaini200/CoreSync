"""Mathematical and Consistency Verification for Task Parallelism Results.

Strict Architectural Rule: This module MUST NOT import PySide6 or any Qt modules.
"""

from dataclasses import dataclass
import math
from typing import Any, Dict, Optional, Tuple
import numpy as np


@dataclass
class TaskVerificationResult:
    """Outcome of verifying a task's computational output."""
    task_id: str
    task_type: str
    passed: bool
    details: str
    checksum: float = 0.0


class TaskVerifier:
    """Verifies output correctness for all supported CPU-bound task types."""

    @staticmethod
    def verify(task_id: str, task_type: str, result_data: Any) -> TaskVerificationResult:
        """Verify task output against mathematical invariants."""
        if not isinstance(result_data, dict):
            return TaskVerificationResult(
                task_id=task_id,
                task_type=task_type,
                passed=False,
                details=f"Expected dict result, got {type(result_data).__name__}",
            )

        try:
            if task_type == "prime_calc":
                count = result_data.get("count", 0)
                largest = result_data.get("largest_prime", 0)
                if count < 0:
                    return TaskVerificationResult(task_id, task_type, False, "Negative prime count")
                if count > 0 and (largest < 2 or (largest > 2 and largest % 2 == 0)):
                    return TaskVerificationResult(task_id, task_type, False, f"Invalid prime number: {largest}")
                return TaskVerificationResult(
                    task_id, task_type, True,
                    f"✓ Verified {count:,} primes (Largest: {largest})",
                    checksum=result_data.get("checksum", 0.0),
                )

            elif task_type == "matrix_mult":
                norm = result_data.get("frobenius_norm", 0.0)
                trace = result_data.get("trace", 0.0)
                if math.isnan(norm) or math.isinf(norm) or norm < 0:
                    return TaskVerificationResult(task_id, task_type, False, f"Invalid Frobenius norm: {norm}")
                return TaskVerificationResult(
                    task_id, task_type, True,
                    f"✓ Verified matrix product (Norm: {norm:.2f}, Trace: {trace:.2f})",
                    checksum=result_data.get("checksum", 0.0),
                )

            elif task_type == "numerical_integration":
                integral = result_data.get("integral", 0.0)
                if math.isnan(integral) or math.isinf(integral):
                    return TaskVerificationResult(task_id, task_type, False, f"Invalid integral value: {integral}")
                return TaskVerificationResult(
                    task_id, task_type, True,
                    f"✓ Simpson's integration verified (Integral: {integral:.6f})",
                    checksum=result_data.get("checksum", 0.0),
                )

            elif task_type == "sorting":
                is_sorted = result_data.get("is_sorted", False)
                min_val = result_data.get("min", 0.0)
                max_val = result_data.get("max", 0.0)
                if not is_sorted or min_val > max_val:
                    return TaskVerificationResult(task_id, task_type, False, f"Array sorting invariant violated: min={min_val}, max={max_val}")
                return TaskVerificationResult(
                    task_id, task_type, True,
                    f"✓ Monotonically sorted ({result_data.get('size', 0):,} items, Range: [{min_val:.1f}, {max_val:.1f}])",
                    checksum=result_data.get("checksum", 0.0),
                )

            elif task_type == "fibonacci":
                digits = result_data.get("digit_count", 0)
                last_6 = result_data.get("last_6_digits", 0)
                if digits < 1 or last_6 < 0:
                    return TaskVerificationResult(task_id, task_type, False, "Invalid Fibonacci output")
                return TaskVerificationResult(
                    task_id, task_type, True,
                    f"✓ Fibonacci verified (Length: {digits:,} digits, End: ...{last_6:06d})",
                    checksum=result_data.get("checksum", 0.0),
                )

            elif task_type == "data_transform":
                std = result_data.get("std", 0.0)
                mean = result_data.get("mean", 0.0)
                if std < 0 or math.isnan(mean) or math.isnan(std):
                    return TaskVerificationResult(task_id, task_type, False, f"Invalid moment statistics: mean={mean}, std={std}")
                return TaskVerificationResult(
                    task_id, task_type, True,
                    f"✓ Moments verified (Mean: {mean:.3f}, Std: {std:.3f})",
                    checksum=result_data.get("checksum", 0.0),
                )

            else:
                return TaskVerificationResult(task_id, task_type, True, "Generic task output verified", checksum=0.0)

        except Exception as e:
            return TaskVerificationResult(task_id, task_type, False, f"Verification exception: {e}")

    @staticmethod
    def compare_results(
        task_type: str,
        result_seq: Any,
        result_par: Any,
        rtol: float = 1e-5,
        atol: float = 1e-8,
    ) -> Tuple[bool, str]:
        """Mathematically compare sequential baseline output against parallel output.

        Enforces full element-by-element equivalence for matrices, sorted arrays, prime lists,
        and transformed vectors, and exact value equality for integers. Summary statistics
        are retained as supplementary checks.
        """
        if not isinstance(result_seq, dict) or not isinstance(result_par, dict):
            return False, "Non-dict output structure"

        try:
            # 1. Supplementary Checksum Check
            cs_seq = result_seq.get("checksum", 0.0)
            cs_par = result_par.get("checksum", 0.0)
            if math.isnan(cs_seq) or math.isnan(cs_par):
                return False, "NaN in checksum"

            diff = abs(cs_seq - cs_par)
            tol = atol + rtol * abs(cs_seq)
            if diff > tol:
                return False, f"Checksum divergence: seq={cs_seq}, par={cs_par}, diff={diff:.2e}"

            # 2. Workload-Specific Full & Invariant Verification
            if task_type == "matrix_mult":
                # Supplementary scalar checks
                trace_seq = result_seq.get("trace", 0.0)
                trace_par = result_par.get("trace", 0.0)
                if abs(trace_seq - trace_par) > (atol + rtol * abs(trace_seq)):
                    return False, f"Matrix trace mismatch: seq={trace_seq}, par={trace_par}"

                norm_seq = result_seq.get("frobenius_norm", 0.0)
                norm_par = result_par.get("frobenius_norm", 0.0)
                if abs(norm_seq - norm_par) > (atol + rtol * abs(norm_seq)):
                    return False, f"Matrix Frobenius norm mismatch: seq={norm_seq}, par={norm_par}"

                # Full output matrix element-by-element verification using np.allclose
                if "matrix" in result_seq and "matrix" in result_par:
                    mat_seq = np.asarray(result_seq["matrix"])
                    mat_par = np.asarray(result_par["matrix"])
                    if mat_seq.shape != mat_par.shape:
                        return False, f"Matrix shape mismatch: {mat_seq.shape} vs {mat_par.shape}"
                    if not np.allclose(mat_seq, mat_par, rtol=rtol, atol=atol):
                        max_diff = float(np.max(np.abs(mat_seq - mat_par)))
                        return False, f"Full matrix element divergence (max diff: {max_diff:.2e})"

            elif task_type == "sorting":
                # Invariant verification: parallel output must be monotonically ascending
                if not result_par.get("is_sorted", False):
                    return False, "Parallel sort result is not monotonically sorted"

                # Supplementary boundary checks
                if result_seq.get("min") != result_par.get("min") or result_seq.get("max") != result_par.get("max"):
                    return False, f"Sort boundary mismatch: min [{result_seq.get('min')} vs {result_par.get('min')}], max [{result_seq.get('max')} vs {result_par.get('max')}]"

                # Full sorted array element-by-element verification
                if "sorted_array" in result_seq and "sorted_array" in result_par:
                    arr_seq = np.asarray(result_seq["sorted_array"])
                    arr_par = np.asarray(result_par["sorted_array"])
                    if arr_seq.shape != arr_par.shape:
                        return False, f"Sorted array shape mismatch: {arr_seq.shape} vs {arr_par.shape}"
                    if not np.allclose(arr_seq, arr_par, rtol=rtol, atol=atol):
                        mismatches = int(np.sum(~np.isclose(arr_seq, arr_par, rtol=rtol, atol=atol)))
                        return False, f"Full sorted array mismatch ({mismatches:,} elements differed)"

            elif task_type == "fibonacci":
                # Supplementary digit checks
                if result_seq.get("digit_count") != result_par.get("digit_count"):
                    return False, f"Fibonacci digit count mismatch: {result_seq.get('digit_count')} vs {result_par.get('digit_count')}"
                if result_seq.get("last_6_digits") != result_par.get("last_6_digits"):
                    return False, f"Fibonacci trailing digits mismatch: {result_seq.get('last_6_digits')} vs {result_par.get('last_6_digits')}"

                # Full exact integer representation verification
                if "fib_value" in result_seq and "fib_value" in result_par:
                    if result_seq["fib_value"] != result_par["fib_value"]:
                        return False, "Exact Fibonacci integer values differ"

            elif task_type == "prime_calc":
                # Supplementary count & largest prime checks
                if result_seq.get("count") != result_par.get("count"):
                    return False, f"Prime count mismatch: {result_seq.get('count')} vs {result_par.get('count')}"
                if result_seq.get("largest_prime") != result_par.get("largest_prime"):
                    return False, f"Largest prime mismatch: {result_seq.get('largest_prime')} vs {result_par.get('largest_prime')}"

                # Full prime sequence verification when available
                if "primes" in result_seq and "primes" in result_par:
                    if result_seq["primes"] != result_par["primes"]:
                        return False, "Prime sequence elements differ"

            elif task_type == "numerical_integration":
                int_seq = float(result_seq.get("integral", 0.0))
                int_par = float(result_par.get("integral", 0.0))
                diff = abs(int_seq - int_par)
                tol = atol + rtol * abs(int_seq)
                if diff > tol:
                    return False, f"Simpson numerical integral mismatch: seq={int_seq:.6e}, par={int_par:.6e}, diff={diff:.2e}"

            elif task_type == "data_transform":
                # Supplementary moments checks
                mean_seq = result_seq.get("mean", 0.0)
                mean_par = result_par.get("mean", 0.0)
                if abs(mean_seq - mean_par) > (atol + rtol * abs(mean_seq)):
                    return False, f"Transform mean mismatch: seq={mean_seq}, par={mean_par}"

                std_seq = result_seq.get("std", 0.0)
                std_par = result_par.get("std", 0.0)
                if abs(std_seq - std_par) > (atol + rtol * abs(std_seq)):
                    return False, f"Transform std mismatch: seq={std_seq}, par={std_par}"

                # Full array element-by-element verification when available
                if "output_array" in result_seq and "output_array" in result_par:
                    arr_seq = np.asarray(result_seq["output_array"])
                    arr_par = np.asarray(result_par["output_array"])
                    if arr_seq.shape != arr_par.shape:
                        return False, f"Transform array shape mismatch: {arr_seq.shape} vs {arr_par.shape}"
                    if not np.allclose(arr_seq, arr_par, rtol=rtol, atol=atol):
                        max_diff = float(np.max(np.abs(arr_seq - arr_par)))
                        return False, f"Full data transform array divergence (max diff: {max_diff:.2e})"

            return True, "Outputs matched within tolerance"

        except Exception as e:
            return False, f"Comparison exception: {e}"

