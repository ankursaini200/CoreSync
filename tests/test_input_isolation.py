"""Unit tests for Benchmark Input Isolation, Deep Cloning, and Buffer Independence."""

import io
import threading
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


def test_numpy_object_array_nested_dictionaries():
    """Verify that NumPy arrays with dtype=object containing nested dicts are deeply isolated."""
    orig = np.empty(2, dtype=object)
    orig[0] = {"alpha": 100, "status": "init"}
    orig[1] = {"beta": 200, "meta": {"sub": [1, 2]}}

    clone = clone_benchmark_input(orig)

    assert isinstance(clone, np.ndarray)
    assert clone.dtype == object
    assert not np.shares_memory(orig, clone)
    # Pointers to nested dicts must NOT be shared
    assert orig[0] is not clone[0]
    assert orig[1] is not clone[1]
    assert orig[1]["meta"] is not clone[1]["meta"]

    # Mutate clone: verify original remains completely unchanged
    clone[0]["alpha"] = 999
    clone[1]["meta"]["sub"].append(3)

    assert orig[0]["alpha"] == 100
    assert orig[1]["meta"]["sub"] == [1, 2]
    assert verify_input_independence(orig, clone)


def test_numpy_object_array_mutable_lists():
    """Verify that NumPy arrays with dtype=object containing mutable lists are deeply isolated."""
    orig = np.empty(3, dtype=object)
    orig[0] = [1, 2, 3]
    orig[1] = [4, 5, 6]
    orig[2] = ["a", "b"]

    clone = clone_benchmark_input(orig)

    assert orig[0] is not clone[0]
    clone[0].append(99)
    clone[2][0] = "MODIFIED"

    assert orig[0] == [1, 2, 3]
    assert orig[2][0] == "a"
    assert clone[0] == [1, 2, 3, 99]
    assert clone[2][0] == "MODIFIED"
    assert verify_input_independence(orig, clone)


def test_custom_clone_returning_self_rejected():
    """Verify that a custom object whose .clone() returns self is rejected with TypeError."""
    class SelfCloner:
        def __init__(self):
            self.val = [1, 2, 3]

        def clone(self):
            return self

    bad_obj = SelfCloner()
    with pytest.raises(TypeError, match="returned original object instance.*self"):
        clone_benchmark_input(bad_obj)


def test_custom_clone_shallow_copy_shared_mutable_rejected():
    """Verify that a custom object whose .clone() performs a shallow copy sharing mutable state is rejected."""
    class ShallowCloner:
        def __init__(self):
            self.config = {"nodes": 4, "timeout": 30}
            self.tags = ["active", "pinned"]

        def clone(self):
            new_obj = ShallowCloner()
            # Intentionally share mutable attributes
            new_obj.config = self.config
            new_obj.tags = self.tags
            return new_obj

    shallow_obj = ShallowCloner()
    with pytest.raises(TypeError, match="returned a shallow copy with shared mutable attribute"):
        clone_benchmark_input(shallow_obj)


def test_valid_independent_custom_clone():
    """Verify that a valid independent custom clone succeeds and mutations do not pollute original."""
    class ValidCloner:
        def __init__(self, name: str, data: list):
            self.name = name
            self.data = list(data)

        def clone(self):
            return ValidCloner(self.name, list(self.data))

    obj = ValidCloner("test_cloner", [10, 20, 30])
    cloned = clone_benchmark_input(obj)

    assert cloned is not obj
    assert cloned.data is not obj.data
    assert cloned.data == [10, 20, 30]

    cloned.data.append(40)
    assert obj.data == [10, 20, 30]
    assert cloned.data == [10, 20, 30, 40]
    assert verify_input_independence(obj, cloned)


def test_unsupported_custom_types_raise_type_error():
    """Verify that custom unpicklable/stateful types without a valid clone handler raise TypeError."""
    class StatefulUnpicklable:
        def __init__(self):
            self.lock = threading.Lock()

    bad_stateful = StatefulUnpicklable()
    with pytest.raises(TypeError, match="Unsupported benchmark input type 'StatefulUnpicklable'"):
        clone_benchmark_input(bad_stateful)
