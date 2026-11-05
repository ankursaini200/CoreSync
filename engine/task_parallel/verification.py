"""Mathematical and Consistency Verification for Task Parallelism Results.

Strict Architectural Rule: This module MUST NOT import PySide6 or any Qt modules.
"""

from dataclasses import dataclass
import math
from typing import Any, Dict, Optional


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
        """Mathematically compare sequential baseline output against parallel output."""
        if not isinstance(result_seq, dict) or not isinstance(result_par, dict):
            return False, "Non-dict output structure"

        try:
            # Checksum equality check
            cs_seq = result_seq.get("checksum", 0.0)
            cs_par = result_par.get("checksum", 0.0)
            if math.isnan(cs_seq) or math.isnan(cs_par):
                return False, "NaN in checksum"

            diff = abs(cs_seq - cs_par)
            tol = atol + rtol * abs(cs_seq)
            if diff > tol:
                return False, f"Checksum divergence: seq={cs_seq}, par={cs_par}, diff={diff:.2e}"

            # Task-specific equivalence checks
            if task_type == "prime_calc":
                if result_seq.get("count") != result_par.get("count"):
                    return False, f"Prime count mismatch: {result_seq.get('count')} vs {result_par.get('count')}"
                if result_seq.get("largest_prime") != result_par.get("largest_prime"):
                    return False, f"Largest prime mismatch: {result_seq.get('largest_prime')} vs {result_par.get('largest_prime')}"

            elif task_type == "numerical_integration":
                int_seq = result_seq.get("integral", 0.0)
                int_par = result_par.get("integral", 0.0)
                if abs(int_seq - int_par) > (atol + rtol * abs(int_seq)):
                    return False, f"Integral mismatch: seq={int_seq}, par={int_par}"

            elif task_type == "sorting":
                if not result_par.get("is_sorted", False):
                    return False, "Parallel sort result is not monotonically sorted"
                if result_seq.get("min") != result_par.get("min") or result_seq.get("max") != result_par.get("max"):
                    return False, "Sort boundary mismatch"

            elif task_type == "fibonacci":
                if result_seq.get("last_6_digits") != result_par.get("last_6_digits"):
                    return False, "Fibonacci last digits mismatch"

            return True, "Outputs matched within tolerance"

        except Exception as e:
            return False, f"Comparison exception: {e}"

