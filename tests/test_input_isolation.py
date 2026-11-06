"""Unit tests for Benchmark Input Isolation, Deep Cloning, and Buffer Independence."""

import io
import numpy as np
import pytest

from engine.analytics.input_cloner import clone_benchmark_input, verify_input_independence
from engine.analytics.benchmarking import BenchmarkingEngine


def test_numpy_array_memory_buffer_independence():
    """Verify cloned NumPy array has an independent memory buffer and zero shared memory."""
    orig = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
    clone = clone_benchmark_input(orig)

    assert isinstance(clone, np.ndarray)
    assert np.array_equal(orig, clone)
    assert not np.shares_memory(orig, clone)
    assert verify_input_independence(orig, clone)

    # Mutate clone: original must remain completely unchanged
    clone[0] = 999.99
    assert orig[0] == 1.0
    assert clone[0] == 999.99


def test_nested_list_containing_mutable_objects():
    """Verify deep recursive isolation for lists with nested mutable dicts and inner lists."""
    orig = [
        {"task_id": "T1", "weights": [10, 20]},
        {"task_id": "T2", "weights": [30, 40]},
    ]
    clone = clone_benchmark_input(orig)

    assert orig == clone
    assert orig is not clone
    assert orig[0] is not clone[0]
    assert orig[0]["weights"] is not clone[0]["weights"]

    # Mutate clone
    clone[0]["weights"][0] = 9999
    clone[1]["task_id"] = "MODIFIED"

    assert orig[0]["weights"][0] == 10
    assert orig[1]["task_id"] == "T2"


def test_nested_dictionary_containing_lists_and_arrays():
    """Verify deep isolation for nested dictionaries containing mixed containers and arrays."""
    orig = {
        "dataset_name": "scientific_eval",
        "parameters": {
            "matrix": np.array([[1.0, 2.0], [3.0, 4.0]]),
            "iterations": 100,
            "bounds": [0.0, 1.0],
        },
        "flags": {"verified": True},
    }
    clone = clone_benchmark_input(orig)

    # Mutate nested array in clone
    clone["parameters"]["matrix"][0, 0] = 888.8
    clone["parameters"]["bounds"][0] = -999.0
    clone["flags"]["verified"] = False

    assert orig["parameters"]["matrix"][0, 0] == 1.0
    assert orig["parameters"]["bounds"][0] == 0.0
    assert orig["flags"]["verified"] is True
    assert not np.shares_memory(orig["parameters"]["matrix"], clone["parameters"]["matrix"])


def test_mutation_by_one_iteration_does_not_affect_subsequent_iteration():
    """Verify that an iteration mutating its input chunk does not pollute subsequent iterations."""
    shared_reference = np.array([10, 20, 30, 40, 50], dtype=np.int32)
    snapshot = shared_reference.copy()

    # Pass 1
    input_pass_1 = clone_benchmark_input(shared_reference)
    input_pass_1 *= 10  # In-place mutation during execution

    # Pass 2
    input_pass_2 = clone_benchmark_input(shared_reference)

    assert np.array_equal(input_pass_2, snapshot)
    assert np.array_equal(shared_reference, snapshot)
    assert not np.array_equal(input_pass_1, snapshot)


def test_unsupported_input_types_fail_clearly():
    """Verify generators and file streams raise explicit TypeError rather than silent shallow sharing."""
    # Generator
    gen = (x * 2 for x in range(10))
    with pytest.raises(TypeError, match="Unsupported benchmark input type 'generator'"):
        clone_benchmark_input(gen)

    # Open file descriptor / StringIO
    stream = io.StringIO("sample payload")
    with pytest.raises(TypeError, match="Unsupported benchmark input type 'StringIO'"):
        clone_benchmark_input(stream)


def test_benchmark_data_parallel_input_equivalence_and_immutability():
    """Verify live DataParallel benchmark passes execute with unmutated, identical initial arrays."""
    from engine.data_parallel.operations import generate_dataset

    raw_data = generate_dataset("transcendental", 5_000)
    original_snapshot = raw_data.copy()

    engine = BenchmarkingEngine()
    session = engine.run_data_parallel_benchmark(
        op_id="transcendental",
        dataset_size=5_000,
        worker_count=2,
        iterations=3,
        warmup_runs=1,
    )

    assert session.verification_passed is True
    assert len(session.measured_records) == 3
    # Check that master data reference was never corrupted
    assert np.array_equal(raw_data, original_snapshot)

