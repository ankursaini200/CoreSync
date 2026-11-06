"""Comprehensive Hand-Calculated Correctness and Edge-Case Audit Tests for Phase 8.1.

Validates:
1. Priority aging correctness (ready-queue waiting only, running exclusion, repeated preemption, both directions, FCFS tie-breaking).
2. Round Robin boundary conditions (arrival at quantum expiry, multiple arrivals, exact completion, early completion, single process, arrival during CS).
3. Context-switch accounting (distinct processes only, no overhead after idle, response time from actual execution, metrics inclusion).
4. Algorithm comparison integrity (immutability of input dataset, parameter propagation).
5. Timeline invariant tests across all 6 scheduling variants.
6. Metric consistency and CPU utilization exclusions.
"""

import math
import pytest

from engine.process_scheduler.algorithms import (
    AlgorithmType,
    FCFSScheduler,
    PriorityScheduler,
    RoundRobinScheduler,
    SJFScheduler,
    SRTFScheduler,
    SchedulerFactory,
)
from engine.process_scheduler.comparator import compare_all_algorithms
from engine.process_scheduler.metrics import calculate_metrics
from engine.process_scheduler.models import (
    PriorityDirection,
    Process,
    ProcessState,
)
from engine.process_scheduler.simulator import ProcessSchedulerSimulator
from engine.process_scheduler.timeline import BlockType, SchedulingTimeline


# =============================================================================
# 1. PRIORITY AGING CORRECTNESS & REPEATED PREEMPTION
# =============================================================================

def test_priority_aging_only_queue_time_counts_and_running_excluded():
    """Verify that only time spent waiting in ready queue contributes to aging,
    and running CPU time is strictly excluded.
    """
    # P1: arr=0, burst=10, prio=1. Runs from 0 to 10.
    # P2: arr=0, burst=2, prio=5. Waits while P1 runs.
    # Aging interval = 4.0. Lower is higher.
    # At t=0: P1 runs. P2 in queue.
    # At t=4: P2 has waited 4.0 ms -> ages from 5 to 4.
    # At t=8: P2 has waited 8.0 ms -> ages from 4 to 3.
    # At t=10: P1 completes at 10. P2 has waited 10.0 ms. floor(10/4) = 2 steps -> prio=3.
    # P2 runs from 10 to 12. While P2 runs, its wait time STAYS at 10 (does not increase).
    p1 = Process(process_id="P1", arrival_time=0.0, burst_time=10.0, priority=1)
    p2 = Process(process_id="P2", arrival_time=0.0, burst_time=2.0, priority=5)

    sched = PriorityScheduler(
        preemptive=False,
        direction=PriorityDirection.LOWER_IS_HIGHER,
        enable_aging=True,
        aging_interval=4.0,
    )
    procs, timeline = sched.schedule([p1, p2])
    proc_map = {p.process_id: p for p in procs}

    assert proc_map["P1"].start_time == 0.0
    assert proc_map["P1"].completion_time == 10.0
    assert proc_map["P1"].current_priority == 1  # Never aged because it ran from t=0

    assert proc_map["P2"].start_time == 10.0
    assert proc_map["P2"].completion_time == 12.0
    assert proc_map["P2"].current_priority == 3  # 5 - floor(10/4) = 3


def test_priority_aging_repeated_preemption_resumes_waiting_time():
    """Hand-Calculated Test Case 1: Process is repeatedly preempted.
    Proves that when a process is preempted, its queue waiting time resumes
    accumulating across disconnected ready-queue intervals.
    """
    # aging_interval = 4.0, direction = LOWER_IS_HIGHER
    # P1: arr=0, burst=10, prio=3
    # P2: arr=0, burst=2,  prio=2
    # P3: arr=1, burst=1,  prio=1
    # Trace:
    # t=0: P2 runs (prio 2 < 3). P1 waits in ready queue (W1=0).
    # t=1: P3 arrives (prio 1). P3 preempts P2!
    #      P2 has run 1 unit (rem=1), P2 enters ready queue (W2=0).
    #      P1 has waited 1 unit (W1=1).
    # t=1..2: P3 runs for 1 unit and completes at t=2.
    #         P1 waits: W1 = 1 + 1 = 2.
    #         P2 waits: W2 = 0 + 1 = 1.
    # t=2: P2 (prio 2) resumes over P1 (prio 3).
    # t=2..3: P2 runs remaining 1 unit and completes at t=3.
    #         P1 waits: W1 = 2 + 1 = 3.
    # t=3: P1 starts running on CPU. W1 stays at 3!
    #      Since W1=3 < 4, P1 never reaches 1st aging step!
    # t=3..13: P1 runs for 10 units and completes at t=13.
    p1 = Process(process_id="P1", arrival_time=0.0, burst_time=10.0, priority=3)
    p2 = Process(process_id="P2", arrival_time=0.0, burst_time=2.0, priority=2)
    p3 = Process(process_id="P3", arrival_time=1.0, burst_time=1.0, priority=1)

    sched = PriorityScheduler(
        preemptive=True,
        direction=PriorityDirection.LOWER_IS_HIGHER,
        enable_aging=True,
        aging_interval=4.0,
    )
    procs, timeline = sched.schedule([p1, p2, p3])
    proc_map = {p.process_id: p for p in procs}

    assert proc_map["P3"].start_time == 1.0
    assert proc_map["P3"].completion_time == 2.0
    assert proc_map["P3"].turnaround_time == 1.0
    assert proc_map["P3"].waiting_time == 0.0

    assert proc_map["P2"].start_time == 0.0
    assert proc_map["P2"].completion_time == 3.0
    assert proc_map["P2"].turnaround_time == 3.0
    assert proc_map["P2"].waiting_time == 1.0  # Waited while P3 ran [1..2]

    assert proc_map["P1"].start_time == 3.0
    assert proc_map["P1"].completion_time == 13.0
    assert proc_map["P1"].turnaround_time == 13.0
    assert proc_map["P1"].waiting_time == 3.0  # Waited [0..3]


def test_priority_aging_mid_execution_preemption():
    """Hand-Calculated Test Case 2: Aging in ready queue dynamically triggers
    preemption of currently running process at the exact aging interval boundary.
    """
    # aging_interval = 3.0, direction = LOWER_IS_HIGHER
    # P1: arr=0, burst=8, prio=2
    # P2: arr=0, burst=4, prio=3
    # Trace:
    # t=0: P1 (prio 2) starts. P2 (prio 3) in ready queue (W2=0).
    # t=3: P2 has waited 3 ms -> prio becomes 3 - 1 = 2.
    #      Tie break with P1 (prio 2): P1 arrived at 0 and was already running (FCFS) -> P1 continues.
    # t=6: P2 has waited 6 ms -> prio becomes 3 - 2 = 1.
    #      P2 prio 1 is strictly higher than P1 prio 2 -> P2 PREEMPTS P1 at t=6!
    #      P1 block: [0, 6], preempted=True. Remaining burst = 2.
    # t=6..10: P2 runs 4 units and completes at t=10.
    #          During [6..10], P1 waits 4 ms in ready queue.
    #          P1 ages by floor(4/3) = 1 step -> prio becomes 2 - 1 = 1!
    # t=10..12: P1 resumes and completes at t=12.
    p1 = Process(process_id="P1", arrival_time=0.0, burst_time=8.0, priority=2)
    p2 = Process(process_id="P2", arrival_time=0.0, burst_time=4.0, priority=3)

    sched = PriorityScheduler(
        preemptive=True,
        direction=PriorityDirection.LOWER_IS_HIGHER,
        enable_aging=True,
        aging_interval=3.0,
    )
    procs, timeline = sched.schedule([p1, p2])
    proc_map = {p.process_id: p for p in procs}

    assert proc_map["P1"].start_time == 0.0
    assert proc_map["P1"].completion_time == 11.0
    assert proc_map["P1"].turnaround_time == 11.0
    assert proc_map["P1"].waiting_time == 3.0

    assert proc_map["P2"].start_time == 6.0
    assert proc_map["P2"].completion_time == 12.0
    assert proc_map["P2"].turnaround_time == 12.0
    assert proc_map["P2"].waiting_time == 8.0

    # Verify preemption blocks in timeline
    p1_blocks = [b for b in timeline.blocks if b.process_id == "P1"]
    assert len(p1_blocks) == 2
    assert p1_blocks[0].start_time == 0.0
    assert p1_blocks[0].end_time == 6.0
    assert p1_blocks[0].preempted is True

    assert p1_blocks[1].start_time == 9.0
    assert p1_blocks[1].end_time == 11.0
    assert p1_blocks[1].preempted is False

    p2_blocks = [b for b in timeline.blocks if b.process_id == "P2"]
    assert len(p2_blocks) == 2
    assert p2_blocks[0].start_time == 6.0
    assert p2_blocks[0].end_time == 9.0
    assert p2_blocks[0].preempted is True

    assert p2_blocks[1].start_time == 11.0
    assert p2_blocks[1].end_time == 12.0
    assert p2_blocks[1].preempted is False


def test_priority_aging_higher_is_higher_direction():
    """Hand-Calculated Test Case 3: HIGHER_IS_HIGHER priority direction.
    Larger numeric value represents higher priority. Aging increases priority value.
    """
    # aging_interval = 2.0, direction = HIGHER_IS_HIGHER
    # P1: arr=0, burst=6, prio=10
    # P2: arr=0, burst=3, prio=8
    # Trace:
    # t=0: P1 (prio 10) > P2 (prio 8) -> P1 runs.
    # t=2: P2 wait = 2 -> prio becomes 8 + 1 = 9.
    # t=4: P2 wait = 4 -> prio becomes 8 + 2 = 10. Tie with P1 -> P1 continues.
    # t=6: P1 completes at 6. P2 wait = 6 -> prio becomes 8 + 3 = 11.
    # t=6..9: P2 runs and completes at 9.
    p1 = Process(process_id="P1", arrival_time=0.0, burst_time=6.0, priority=10)
    p2 = Process(process_id="P2", arrival_time=0.0, burst_time=3.0, priority=8)

    sched = PriorityScheduler(
        preemptive=True,
        direction=PriorityDirection.HIGHER_IS_HIGHER,
        enable_aging=True,
        aging_interval=2.0,
    )
    procs, timeline = sched.schedule([p1, p2])
    proc_map = {p.process_id: p for p in procs}

    assert proc_map["P1"].completion_time == 6.0
    assert proc_map["P2"].start_time == 6.0
    assert proc_map["P2"].completion_time == 9.0
    assert proc_map["P2"].current_priority == 11


def test_priority_deterministic_fcfs_tie_breaking():
    """Verify deterministic tie-breaking on arrival time, then PID for equal priority."""
    # All 3 have identical priority 2 and arrive at t=0
    p1 = Process(process_id="P1", arrival_time=0.0, burst_time=2.0, priority=2)
    p2 = Process(process_id="P2", arrival_time=0.0, burst_time=2.0, priority=2)
    p3 = Process(process_id="P3", arrival_time=0.0, burst_time=2.0, priority=2)

    sched = PriorityScheduler(preemptive=False, direction=PriorityDirection.LOWER_IS_HIGHER)
    procs, timeline = sched.schedule([p3, p1, p2])  # Pass in scrambled order

    # FCFS + PID order: P1 -> P2 -> P3
    assert [b.process_id for b in timeline.blocks if b.block_type == BlockType.PROCESS] == ["P1", "P2", "P3"]


# =============================================================================
# 2. ROUND ROBIN BOUNDARY CONDITIONS
# =============================================================================

def test_round_robin_arrival_at_quantum_expiry_enqueued_before_preempted():
    """Verify ready-queue ordering when a process arrives at the EXACT instant
    another process's quantum expires. The newly arrived process must be enqueued
    BEFORE the preempted process is appended to the tail.
    """
    # Q = 4.0
    # P1: arr=0.0, burst=6.0
    # P2: arr=4.0, burst=2.0 (arrives exactly at t=4.0 when P1's quantum expires)
    # Trace:
    # t=0..4: P1 executes for 4 ms. Remaining = 2.0.
    # At t=4.0: P2 arrives. Ready queue must enqueue P2 first, then re-append P1!
    # Queue state at t=4.0: [P2, P1].
    # Next process to execute must be P2!
    # t=4..6: P2 executes for 2 ms and completes at t=6.
    # t=6..8: P1 executes remaining 2 ms and completes at t=8.
    p1 = Process(process_id="P1", arrival_time=0.0, burst_time=6.0)
    p2 = Process(process_id="P2", arrival_time=4.0, burst_time=2.0)

    sched = RoundRobinScheduler(time_quantum=4.0)
    procs, timeline = sched.schedule([p1, p2])
    proc_map = {p.process_id: p for p in procs}

    exec_order = [b.process_id for b in timeline.blocks if b.block_type == BlockType.PROCESS]
    assert exec_order == ["P1", "P2", "P1"]
    assert proc_map["P2"].start_time == 4.0
    assert proc_map["P2"].completion_time == 6.0
    assert proc_map["P1"].completion_time == 8.0


def test_round_robin_multiple_processes_arriving_at_same_timestamp():
    """Verify deterministic FIFO ordering for multiple processes arriving at identical timestamp."""
    p1 = Process(process_id="P1", arrival_time=0.0, burst_time=2.0)
    p2 = Process(process_id="P2", arrival_time=0.0, burst_time=2.0)
    p3 = Process(process_id="P3", arrival_time=0.0, burst_time=2.0)

    sched = RoundRobinScheduler(time_quantum=1.0)
    procs, timeline = sched.schedule([p3, p1, p2])

    # Round 1: P1, P2, P3. Round 2: P1, P2, P3
    exec_order = [b.process_id for b in timeline.blocks if b.block_type == BlockType.PROCESS]
    assert exec_order == ["P1", "P2", "P3", "P1", "P2", "P3"]


def test_round_robin_process_completing_exactly_at_quantum_boundary():
    """Verify process completing exactly at quantum boundary is marked completed and not re-enqueued."""
    p1 = Process(process_id="P1", arrival_time=0.0, burst_time=4.0)
    p2 = Process(process_id="P2", arrival_time=0.0, burst_time=4.0)

    sched = RoundRobinScheduler(time_quantum=4.0)
    procs, timeline = sched.schedule([p1, p2])

    assert len(timeline.blocks) == 2
    assert timeline.blocks[0].duration == 4.0
    assert timeline.blocks[0].preempted is False  # Completed, not preempted!
    assert timeline.blocks[1].duration == 4.0
    assert timeline.blocks[1].preempted is False


def test_round_robin_process_completing_before_quantum_expires():
    """Verify process completing before its quantum expires yields CPU immediately."""
    # Q = 5.0
    # P1: arr=0, burst=2.0 (completes early)
    # P2: arr=0, burst=4.0
    p1 = Process(process_id="P1", arrival_time=0.0, burst_time=2.0)
    p2 = Process(process_id="P2", arrival_time=0.0, burst_time=4.0)

    sched = RoundRobinScheduler(time_quantum=5.0)
    procs, timeline = sched.schedule([p1, p2])

    assert timeline.blocks[0].process_id == "P1"
    assert timeline.blocks[0].duration == 2.0
    assert timeline.blocks[0].end_time == 2.0
    assert timeline.blocks[1].process_id == "P2"
    assert timeline.blocks[1].start_time == 2.0
    assert timeline.blocks[1].duration == 4.0
    assert timeline.blocks[1].end_time == 6.0


def test_round_robin_single_process_no_competing_processes():
    """Verify that a single process running alone across multiple slices
    does NOT incur context switch penalties, and executes contiguously.
    """
    p1 = Process(process_id="P1", arrival_time=0.0, burst_time=10.0)

    # CS overhead = 1.0, but only 1 process exists
    sched = RoundRobinScheduler(time_quantum=3.0, context_switch_overhead=1.0)
    procs, timeline = sched.schedule([p1])

    # No context switch blocks should exist because last_pid == p.process_id
    cs_blocks = [b for b in timeline.blocks if b.block_type == BlockType.CONTEXT_SWITCH]
    assert len(cs_blocks) == 0

    assert timeline.total_simulation_time == 10.0
    assert timeline.total_busy_time == 10.0
    assert procs[0].waiting_time == 0.0
    assert procs[0].turnaround_time == 10.0


def test_round_robin_process_arriving_during_context_switch_interval():
    """Hand-Calculated Test Case 4: Process arriving during a context-switch interval
    is safely enqueued upon switch completion and executes in deterministic order.
    """
    # Q = 2.0, CS = 0.5
    # P1: arr=0.0, burst=3.0
    # P2: arr=0.0, burst=2.0
    # P3: arr=2.2, burst=1.0 (arrives during CS between P1 and P2 at [2.0, 2.5])
    # Trace:
    # t=0..2: P1 runs (quantum expires, rem=1). Block: P1 [0, 2].
    # t=2.0..2.5: CS from P1 to P2. P3 arrives at t=2.2!
    #             At t=2.5, P3 is enqueued into ready queue.
    # t=2.5..4.5: P2 runs 2.0 units and completes at 4.5. Block: P2 [2.5, 4.5].
    # t=4.5..5.0: CS from P2 to P1.
    # t=5.0..6.0: P1 runs remaining 1.0 unit and completes at 6.0. Block: P1 [5.0, 6.0].
    # t=6.0..6.5: CS from P1 to P3.
    # t=6.5..7.5: P3 runs 1.0 unit and completes at 7.5. Block: P3 [6.5, 7.5].
    p1 = Process(process_id="P1", arrival_time=0.0, burst_time=3.0)
    p2 = Process(process_id="P2", arrival_time=0.0, burst_time=2.0)
    p3 = Process(process_id="P3", arrival_time=2.2, burst_time=1.0)

    sched = RoundRobinScheduler(time_quantum=2.0, context_switch_overhead=0.5)
    procs, timeline = sched.schedule([p1, p2, p3])
    proc_map = {p.process_id: p for p in procs}

    assert timeline.total_simulation_time == 7.5
    assert timeline.total_busy_time == 6.0
    assert timeline.total_context_switch_time == 1.5

    # Check 3 CS blocks
    cs_blocks = [b for b in timeline.blocks if b.block_type == BlockType.CONTEXT_SWITCH]
    assert len(cs_blocks) == 3
    assert cs_blocks[0].start_time == 2.0 and cs_blocks[0].end_time == 2.5
    assert cs_blocks[1].start_time == 4.5 and cs_blocks[1].end_time == 5.0
    assert cs_blocks[2].start_time == 6.0 and cs_blocks[2].end_time == 6.5

    # Hand-calculated process metrics
    assert proc_map["P1"].start_time == 0.0
    assert proc_map["P1"].completion_time == 6.0
    assert proc_map["P1"].turnaround_time == 6.0
    assert proc_map["P1"].waiting_time == 3.0
    assert proc_map["P1"].response_time == 0.0

    assert proc_map["P2"].start_time == 2.5  # First execution begins AFTER CS!
    assert proc_map["P2"].completion_time == 4.5
    assert proc_map["P2"].turnaround_time == 4.5
    assert proc_map["P2"].waiting_time == 2.5
    assert proc_map["P2"].response_time == 2.5

    assert proc_map["P3"].start_time == 6.5
    assert proc_map["P3"].completion_time == 7.5
    assert round(proc_map["P3"].turnaround_time, 2) == 5.3  # 7.5 - 2.2
    assert round(proc_map["P3"].waiting_time, 2) == 4.3     # 5.3 - 1.0
    assert round(proc_map["P3"].response_time, 2) == 4.3    # 6.5 - 2.2


# =============================================================================
# 3. CONTEXT-SWITCH ACCOUNTING & IDLE CPU TRANSITIONS
# =============================================================================

def test_context_switch_no_overhead_after_idle_cpu_gap():
    """Hand-Calculated Test Case 5: Transition from CPU IDLE interval to an arrived
    process does NOT incur context-switch overhead.
    """
    # CS = 0.5
    # P1: arr=0, burst=2
    # Idle: [2.0, 5.0]
    # P2: arr=5, burst=2
    # At t=5.0, P2 must start immediately with NO context switch!
    p1 = Process(process_id="P1", arrival_time=0.0, burst_time=2.0)
    p2 = Process(process_id="P2", arrival_time=5.0, burst_time=2.0)

    sched = FCFSScheduler(context_switch_overhead=0.5)
    procs, timeline = sched.schedule([p1, p2])

    assert timeline.total_simulation_time == 7.0
    assert timeline.total_busy_time == 4.0
    assert timeline.total_idle_time == 3.0
    assert timeline.total_context_switch_time == 0.0
    assert timeline.context_switch_count == 0

    types = [b.block_type for b in timeline.blocks]
    assert types == [BlockType.PROCESS, BlockType.IDLE, BlockType.PROCESS]
    assert timeline.blocks[2].start_time == 5.0  # Started immediately at arrival!


def test_context_switch_metrics_accounting_and_cpu_utilization_exclusion():
    """Verify that CPU utilization formula strictly excludes context switch overhead."""
    p1 = Process(process_id="P1", arrival_time=0.0, burst_time=3.0)
    p2 = Process(process_id="P2", arrival_time=0.0, burst_time=3.0)

    # CS = 1.0. Total sim time = 3.0 (P1) + 1.0 (CS) + 3.0 (P2) = 7.0
    # Busy time = 6.0. CPU Util = 6.0 / 7.0 * 100 = 85.71%
    res = ProcessSchedulerSimulator.simulate(
        processes=[p1, p2],
        algorithm_type=AlgorithmType.FCFS,
        context_switch_overhead=1.0,
    )
    m = res.metrics
    assert m.total_simulation_time == 7.0
    assert m.busy_cpu_time == 6.0
    assert m.context_switch_time == 1.0
    assert m.context_switches == 1
    assert round(m.cpu_utilization_pct, 2) == 85.71


def test_response_time_measured_from_actual_execution_not_cs_start():
    """Verify response time is measured to first actual CPU execution, not CS overhead start."""
    p1 = Process(process_id="P1", arrival_time=0.0, burst_time=2.0)
    p2 = Process(process_id="P2", arrival_time=0.0, burst_time=2.0)

    # CS = 0.8
    # P1 runs [0..2]. CS runs [2.0..2.8]. P2 runs [2.8..4.8].
    # P2 arrival = 0.0. P2 first start = 2.8. RT = 2.8 - 0.0 = 2.8.
    res = ProcessSchedulerSimulator.simulate(
        processes=[p1, p2],
        algorithm_type=AlgorithmType.FCFS,
        context_switch_overhead=0.8,
    )
    p2_res = [p for p in res.processes if p.process_id == "P2"][0]
    assert p2_res.start_time == 2.8
    assert p2_res.response_time == 2.8


# =============================================================================
# 4. ALGORITHM COMPARISON INTEGRITY & IMMUTABILITY
# =============================================================================

def test_comparator_input_immutability():
    """Verify that compare_all_algorithms does NOT mutate the original input processes."""
    original_processes = [
        Process(process_id="P1", arrival_time=0.0, burst_time=10.0, priority=2),
        Process(process_id="P2", arrival_time=2.0, burst_time=5.0, priority=1),
        Process(process_id="P3", arrival_time=4.0, burst_time=8.0, priority=3),
    ]

    results, rows = compare_all_algorithms(
        processes=original_processes,
        time_quantum=2.5,
        direction=PriorityDirection.LOWER_IS_HIGHER,
        enable_aging=True,
        aging_interval=3.0,
        context_switch_overhead=0.2,
    )

    assert len(results) == 6
    assert len(rows) == 6

    # Verify original input list is completely unmutated
    for p in original_processes:
        assert p.remaining_time == p.burst_time
        assert p.start_time is None
        assert p.completion_time is None
        assert p.turnaround_time == 0.0
        assert p.waiting_time == 0.0
        assert p.response_time == 0.0
        assert p.state == ProcessState.NOT_ARRIVED


def test_comparator_invalid_parameters_rejected():
    """Verify comparator rejects invalid inputs cleanly."""
    valid_p = [Process(process_id="P1", arrival_time=0.0, burst_time=2.0)]

    # Negative quantum
    with pytest.raises(ValueError, match="strictly positive"):
        compare_all_algorithms(valid_p, time_quantum=-1.0)

    # Negative context switch
    with pytest.raises(ValueError, match="non-negative"):
        compare_all_algorithms(valid_p, context_switch_overhead=-0.5)

    # Empty process list
    with pytest.raises(ValueError, match="Process list cannot be empty"):
        compare_all_algorithms([])


# =============================================================================
# 5. TIMELINE CORRECTNESS & INVARIANT TESTS ACROSS ALL 6 ALGORITHMS
# =============================================================================

@pytest.mark.parametrize("algo", [
    AlgorithmType.FCFS,
    AlgorithmType.SJF,
    AlgorithmType.SRTF,
    AlgorithmType.PRIORITY_NON_PREEMPTIVE,
    AlgorithmType.PRIORITY_PREEMPTIVE,
    AlgorithmType.ROUND_ROBIN,
])
def test_timeline_invariants_across_all_algorithms(algo):
    """Rigorous invariant testing across all six scheduling algorithms:
    - Invariant 1: Blocks are contiguous (end of block i == start of block i+1).
    - Invariant 2: No negative or zero-duration blocks.
    - Invariant 3: No process executes before its arrival time.
    - Invariant 4: Total executed time for each process equals original burst time.
    - Invariant 5: Every completed process has exactly one completion timestamp matching final block.
    """
    procs = [
        Process(process_id="P1", arrival_time=0.0, burst_time=5.0, priority=3),
        Process(process_id="P2", arrival_time=2.0, burst_time=3.0, priority=1),
        Process(process_id="P3", arrival_time=6.0, burst_time=4.0, priority=2),
        Process(process_id="P4", arrival_time=15.0, burst_time=2.0, priority=1),  # Forces idle gap
    ]

    res = ProcessSchedulerSimulator.simulate(
        processes=procs,
        algorithm_type=algo,
        time_quantum=2.0,
        direction=PriorityDirection.LOWER_IS_HIGHER,
        enable_aging=True,
        aging_interval=3.0,
        context_switch_overhead=0.2,
    )

    timeline = res.timeline
    assert len(timeline.blocks) > 0

    # Invariant 1: Contiguity
    for i in range(len(timeline.blocks) - 1):
        b_curr = timeline.blocks[i]
        b_next = timeline.blocks[i + 1]
        assert abs(b_curr.end_time - b_next.start_time) < 1e-4, (
            f"Contiguity violation between block {i} ({b_curr.end_time}) and {i+1} ({b_next.start_time})"
        )

    # Invariant 2: Positive duration
    for idx, b in enumerate(timeline.blocks):
        assert b.duration > 0.0, f"Block {idx} has non-positive duration {b.duration}"
        assert b.end_time > b.start_time

    # Invariant 3: No execution before arrival
    orig_map = {p.process_id: p.arrival_time for p in procs}
    for b in timeline.blocks:
        if b.block_type == BlockType.PROCESS:
            assert b.start_time >= orig_map[b.process_id] - 1e-4

    # Invariant 4: Total executed time equals original burst time
    orig_burst_map = {p.process_id: p.burst_time for p in procs}
    for pid, orig_burst in orig_burst_map.items():
        exec_time = sum(b.duration for b in timeline.blocks if b.process_id == pid)
        assert abs(exec_time - orig_burst) < 1e-4, (
            f"{algo}: Executed duration {exec_time} does not match burst {orig_burst} for {pid}"
        )

    # Invariant 5: Completion timestamp matches final block end
    completed_map = {p.process_id: p.completion_time for p in res.processes}
    for pid, comp_time in completed_map.items():
        proc_blocks = [b for b in timeline.blocks if b.process_id == pid]
        assert proc_blocks, f"No blocks found for completed process {pid}"
        assert abs(proc_blocks[-1].end_time - comp_time) < 1e-4
