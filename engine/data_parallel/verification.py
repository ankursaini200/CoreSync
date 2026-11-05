"""Correctness Verification Engine for Data Parallelism.

Numerically verifies parallel chunk execution outputs against sequential baselines.
Enforces strict floating-point and integer tolerances and provides diagnostic metrics.
"""

from dataclasses import dataclass
import math
from typing import Any
import numpy as np


@dataclass(frozen=True)
class VerificationResult:
    """Consolidated numerical correctness report."""
    passed: bool
    mismatch_count: int
    total_items: int
    max_difference: float
    mean_difference: float
    rtol: float
    atol: float
    status_message: str


class ResultVerifier:
    """Verifies that parallel and sequential computations produce identical outputs."""

    @staticmethod
    def verify(
        sequential_result: Any,
        parallel_result: Any,
        is_reduction: bool = False,
        rtol: float = 1e-5,
        atol: float = 1e-8,
    ) -> VerificationResult:
        """Compare sequential baseline against merged parallel output.

        Args:
            sequential_result: Result from sequential execution.
            parallel_result: Result from parallel execution.
            is_reduction: True if result is a scalar reduction, False if array.
            rtol: Relative numerical tolerance.
            atol: Absolute numerical tolerance.

        Returns:
            VerificationResult instance.
        """
        # Case 1: Scalar Reduction
        if is_reduction:
            if isinstance(sequential_result, (int, np.integer)) and isinstance(parallel_result, (int, np.integer)):
                diff = abs(int(sequential_result) - int(parallel_result))
                passed = (diff == 0)
                msg = "Exact integer match (0 differences)" if passed else f"Integer mismatch: {sequential_result} != {parallel_result}"
                return VerificationResult(
                    passed=passed,
                    mismatch_count=0 if passed else 1,
                    total_items=1,
                    max_difference=float(diff),
                    mean_difference=float(diff),
                    rtol=0.0,
                    atol=0.0,
                    status_message=msg,
                )
            else:
                s_val = float(sequential_result)
                p_val = float(parallel_result)
                diff = abs(s_val - p_val)
                passed = math.isclose(s_val, p_val, rel_tol=rtol, abs_tol=atol)
                msg = f"Scalar within tolerance (diff={diff:.2e})" if passed else f"Scalar mismatch exceeded tolerance: diff={diff:.2e}"
                return VerificationResult(
                    passed=passed,
                    mismatch_count=0 if passed else 1,
                    total_items=1,
                    max_difference=diff,
                    mean_difference=diff,
                    rtol=rtol,
                    atol=atol,
                    status_message=msg,
                )

        # Case 2: Array Output
        if not isinstance(sequential_result, np.ndarray) or not isinstance(parallel_result, np.ndarray):
            return VerificationResult(
                passed=False,
                mismatch_count=1,
                total_items=0,
                max_difference=float("nan"),
                mean_difference=float("nan"),
                rtol=rtol,
                atol=atol,
                status_message=f"Type mismatch: sequential is {type(sequential_result).__name__}, parallel is {type(parallel_result).__name__}",
            )

        if sequential_result.shape != parallel_result.shape:
            return VerificationResult(
                passed=False,
                mismatch_count=sequential_result.size,
                total_items=sequential_result.size,
                max_difference=float("nan"),
                mean_difference=float("nan"),
                rtol=rtol,
                atol=atol,
                status_message=f"Shape mismatch: {sequential_result.shape} != {parallel_result.shape}",
            )

        total_items = sequential_result.size
        if total_items == 0:
            return VerificationResult(
                passed=True,
                mismatch_count=0,
                total_items=0,
                max_difference=0.0,
                mean_difference=0.0,
                rtol=rtol,
                atol=atol,
                status_message="Empty arrays verified (0 elements)",
            )

        # Numerical comparison with tolerance
        close_mask = np.isclose(sequential_result, parallel_result, rtol=rtol, atol=atol)
        mismatches = int(np.count_nonzero(~close_mask))
        diff_array = np.abs(sequential_result - parallel_result)
        max_diff = float(np.max(diff_array))
        mean_diff = float(np.mean(diff_array))

        passed = (mismatches == 0)
        if passed:
            msg = f"Verified: 100% matched ({total_items:,} items, max diff={max_diff:.2e})"
        else:
            pct_err = (mismatches / total_items) * 100.0
            msg = f"FAILED: {mismatches:,} mismatches ({pct_err:.2f}%), max diff={max_diff:.2e}"

        return VerificationResult(
            passed=passed,
            mismatch_count=mismatches,
            total_items=total_items,
            max_difference=max_diff,
            mean_difference=mean_diff,
            rtol=rtol,
            atol=atol,
            status_message=msg,
        )

