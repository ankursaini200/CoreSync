"""Comprehensive Unit and Verification Tests for CPU Scheduling Simulator.

Strict Architectural Rule: Pure Python testing without PySide6 GUI dependencies.
Includes exact hand-calculated test cases verifying execution orders, timestamps,
idle intervals, preemption, context-switch overheads, priority aging, and metrics.
"""

import pytest

from engine.process_scheduler import (
    AlgorithmType,
    BlockType,
    ComparisonSummaryRow,
    FCFSScheduler,
    PriorityDirection,
    PriorityScheduler,
    Process,
    ProcessSchedulerSimulator,
    ProcessState,
    RoundRobinScheduler,
    SJFScheduler,
    SRTFScheduler,
    SchedulingMetrics,
    compare_all_algorithms,
    get_all_presets,
    get_preset_by_id,
    validate_context_switch,
    validate_process,
    validate_process_list,
    validate_quantum,
)


# -----------------------------------------------------------------------------
# 1. Input Validation and Model Integrity
# -----------------------------------------------------------------------------
def test_process_validation_success():
    """Verify valid process initialization and cloning."""
    p = Process(process_id="P1", arrival_time=0.0, burst_time=5.0, priority=2)
    assert p.process_id == "P1"
    assert p.arrival_time == 0.0
    assert p.burst_time == 5.0
    assert p.remaining_time == 5.0
    assert p.priority == 2
    assert p.current_priority == 2
    assert p.state == ProcessState.NOT_ARRIVED

    clone = p.clone()
    assert clone.process_id == "P1"
    assert clone is not p


def test_process_validation_rejects_negative_arrival():
    """Verify rejection of negative arrival time."""
    p = Process(process_id="P_NEG", arrival_time=-1.0, burst_time=5.0)
    with pytest.raises(ValueError, match="Arrival time must be non-negative"):
        validate_process(p)


def test_process_validation_rejects_non_positive_burst():
    """Verify rejection of zero or negative burst time."""
    p_zero = Process(process_id="P0", arrival_time=0.0, burst_time=0.0)
    with pytest.raises(ValueError, match="Burst time must be strictly positive"):
        validate_process(p_zero)

    p_neg = Process(process_id="P_NEG", arrival_time=0.0, burst_time=-4.0)
    with pytest.raises(ValueError, match="Burst time must be strictly positive"):
        validate_process(p_neg)


def test_process_validation_rejects_duplicate_pids():
    """Verify rejection of duplicate process IDs in a batch."""
    procs = [
        Process(process_id="P1", arrival_time=0.0, burst_time=4.0),
        Process(process_id="P1", arrival_time=1.0, burst_time=2.0),
    ]
    with pytest.raises(ValueError, match="Duplicate process ID detected"):
        validate_process_list(procs)


def test_process_validation_rejects_empty_list():
    """Verify rejection of empty process list."""
    with pytest.raises(ValueError, match="Process list cannot be empty"):
        validate_process_list([])


def test_validation_quantum_and_context_switch():
    """Verify rejection of invalid time quantum and negative overhead."""
    with pytest.raises(ValueError, match="Time quantum must be strictly positive"):
        validate_quantum(0.0)
    with pytest.raises(ValueError, match="Time quantum must be strictly positive"):
        validate_quantum(-2.0)

    with pytest.raises(ValueError, match="Overhead must be non-negative"):
        validate_context_switch(-0.5)

    # Valid values should not raise
    validate_quantum(2.5)
    validate_context_switch(0.0)
    validate_context_switch(0.5)


# -----------------------------------------------------------------------------
# 2. Hand-Calculated Test Case: FCFS with Idle Gap & Staggered Arrivals
# -----------------------------------------------------------------------------
def test_hand_calculated_fcfs_with_idle_gap():
    """Verify hand-calculated FCFS execution with CPU idle interval.

    Hand-calculated expectation:
        P1: arr=0, burst=4  -> runs [0..4]   (start=0, finish=4, TAT=4, WT=0, RT=0)
        P2: arr=1, burst=3  -> runs [4..7]   (start=4, finish=7, TAT=6, WT=3, RT=3)
        IDLE: [7..8]
        P3: arr=8, burst=2  -> runs [8..10]  (start=8, finish=10, TAT=2, WT=0, RT=0)

        Total simulation time = 10.0
        Busy CPU time = 9.0
        Idle CPU time = 1.0
        Avg TAT = (4 + 6 + 2) / 3 = 4.0
        Avg WT  = (0 + 3 + 0) / 3 = 1.0
        Avg RT  = (0 + 3 + 0) / 3 = 1.0
        CPU Utilization = 90.0%
        Throughput = 3 / 10 = 0.3
    """
    procs = [
        Process(process_id="P1", arrival_time=0.0, burst_time=4.0),
        Process(process_id="P2", arrival_time=1.0, burst_time=3.0),
        Process(process_id="P3", arrival_time=8.0, burst_time=2.0),
    ]

    result = ProcessSchedulerSimulator.simulate(
        processes=procs,
        algorithm_type=AlgorithmType.FCFS,
    )

    p_map = {p.process_id: p for p in result.processes}
    # Per-process verification
    assert p_map["P1"].start_time == 0.0
    assert p_map["P1"].completion_time == 4.0
    assert p_map["P1"].turnaround_time == 4.0
    assert p_map["P1"].waiting_time == 0.0
    assert p_map["P1"].response_time == 0.0

    assert p_map["P2"].start_time == 4.0
    assert p_map["P2"].completion_time == 7.0
    assert p_map["P2"].turnaround_time == 6.0
    assert p_map["P2"].waiting_time == 3.0
    assert p_map["P2"].response_time == 3.0

    assert p_map["P3"].start_time == 8.0
    assert p_map["P3"].completion_time == 10.0
    assert p_map["P3"].turnaround_time == 2.0
    assert p_map["P3"].waiting_time == 0.0
    assert p_map["P3"].response_time == 0.0

    # Summary metrics verification
    m = result.metrics
    assert m.total_simulation_time == 10.0
    assert m.busy_cpu_time == 9.0
    assert m.idle_cpu_time == 1.0
    assert m.average_turnaround_time == 4.0
    assert m.average_waiting_time == 1.0
    assert m.average_response_time == 1.0
    assert m.cpu_utilization_pct == 90.0
    assert m.throughput == 0.3

    # Timeline event inspection
    blocks = result.timeline.blocks
    assert len(blocks) == 4
    assert blocks[0].block_type == BlockType.PROCESS and blocks[0].process_id == "P1"
    assert blocks[1].block_type == BlockType.PROCESS and blocks[1].process_id == "P2"
    assert blocks[2].block_type == BlockType.IDLE and blocks[2].start_time == 7.0 and blocks[2].end_time == 8.0
    assert blocks[3].block_type == BlockType.PROCESS and blocks[3].process_id == "P3"


# -----------------------------------------------------------------------------
# 3. Hand-Calculated Test Case: SJF Non-Preemptive
# -----------------------------------------------------------------------------
def test_hand_calculated_sjf_non_preemptive():
    """Verify hand-calculated SJF non-preemptive execution and tie-breaking.

    Workload:
        P1: arr=0, burst=7
        P2: arr=2, burst=4
        P3: arr=4, burst=1
        P4: arr=5, burst=4

    Hand-calculated expectation:
        At t=0: only P1 ready -> P1 runs [0..7] (C=7, TAT=7, WT=0, RT=0)
        At t=7: P2(4), P3(1), P4(4) ready -> P3 shortest -> P3 runs [7..8] (C=8, TAT=4, WT=3, RT=3)
        At t=8: P2(4, arr=2) vs P4(4, arr=5) -> equal burst! Tie-break by arrival time -> P2 runs [8..12] (C=12, TAT=10, WT=6, RT=6)
        At t=12: P4 runs [12..16] (C=16, TAT=11, WT=7, RT=7)

        Avg TAT = (7 + 10 + 4 + 11) / 4 = 32 / 4 = 8.0
        Avg WT  = (0 + 6 + 3 + 7) / 4 = 16 / 4 = 4.0
        Avg RT  = 4.0
        CPU Utilization = 100.0%
    """
    procs = [
        Process(process_id="P1", arrival_time=0.0, burst_time=7.0),
        Process(process_id="P2", arrival_time=2.0, burst_time=4.0),
        Process(process_id="P3", arrival_time=4.0, burst_time=1.0),
        Process(process_id="P4", arrival_time=5.0, burst_time=4.0),
    ]

    result = ProcessSchedulerSimulator.simulate(
        processes=procs,
        algorithm_type=AlgorithmType.SJF,
    )

    p_map = {p.process_id: p for p in result.processes}
    assert p_map["P1"].completion_time == 7.0
    assert p_map["P3"].completion_time == 8.0
    assert p_map["P2"].completion_time == 12.0
    assert p_map["P4"].completion_time == 16.0

    m = result.metrics
    assert m.average_turnaround_time == 8.0
    assert m.average_waiting_time == 4.0
    assert m.average_response_time == 4.0
    assert m.cpu_utilization_pct == 100.0

    # Verify execution order in timeline
    execution_order = [b.process_id for b in result.timeline.blocks if b.block_type == BlockType.PROCESS]
    assert execution_order == ["P1", "P3", "P2", "P4"]


# -----------------------------------------------------------------------------
# 4. Hand-Calculated Test Case: SRTF (Preemptive SJF)
# -----------------------------------------------------------------------------
def test_hand_calculated_srtf_preemption():
    """Verify hand-calculated Shortest Remaining Time First (SRTF) preemption.

    Workload:
        P1: arr=0, burst=8
        P2: arr=1, burst=4
        P3: arr=2, burst=9
        P4: arr=3, burst=5

    Hand-calculated expectation:
        t=0: P1 starts (runs [0..1], remaining=7)
        t=1: P2 arrives with burst 4 < 7 -> P1 PREEMPTED! P2 starts
        t=2: P3 arrives (burst 9 > 3) -> P2 continues
        t=3: P4 arrives (burst 5 > 2) -> P2 continues
        t=5: P2 finishes! (C=5, TAT=4, WT=0, RT=0)
             Queue: P4(5), P1(7), P3(9) -> P4 runs [5..10] (C=10, TAT=7, WT=2, RT=2)
        t=10: P4 finishes! Queue: P1(7), P3(9) -> P1 resumes [10..17] (C=17, TAT=17, WT=9, RT=0)
        t=17: P1 finishes! Queue: P3(9) -> P3 runs [17..26] (C=26, TAT=24, WT=15, RT=15)

        Avg TAT = (17 + 4 + 24 + 7) / 4 = 52 / 4 = 13.0
        Avg WT  = (9 + 0 + 15 + 2) / 4 = 26 / 4 = 6.5
        Avg RT  = (0 + 0 + 15 + 2) / 4 = 17 / 4 = 4.25
        Total Time = 26.0
    """
    procs = [
        Process(process_id="P1", arrival_time=0.0, burst_time=8.0),
        Process(process_id="P2", arrival_time=1.0, burst_time=4.0),
        Process(process_id="P3", arrival_time=2.0, burst_time=9.0),
        Process(process_id="P4", arrival_time=3.0, burst_time=5.0),
    ]

    result = ProcessSchedulerSimulator.simulate(
        processes=procs,
        algorithm_type=AlgorithmType.SRTF,
    )

    p_map = {p.process_id: p for p in result.processes}
    assert p_map["P2"].completion_time == 5.0
    assert p_map["P4"].completion_time == 10.0
    assert p_map["P1"].completion_time == 17.0
    assert p_map["P3"].completion_time == 26.0

    m = result.metrics
    assert m.total_simulation_time == 26.0
    assert m.average_turnaround_time == 13.0
    assert m.average_waiting_time == 6.5
    assert m.average_response_time == 4.25

    # Check timeline blocks and preemption flag
    blocks = result.timeline.blocks
    assert blocks[0].process_id == "P1" and blocks[0].end_time == 1.0 and blocks[0].preempted is True
    assert blocks[1].process_id == "P2" and blocks[1].end_time == 5.0 and blocks[1].preempted is False


# -----------------------------------------------------------------------------
# 5. Hand-Calculated Test Case: Priority Non-Preemptive vs Preemptive
# -----------------------------------------------------------------------------
def test_hand_calculated_priority_non_preemptive_vs_preemptive():
    """Verify hand-calculated Priority Scheduling in both modes.

    Workload (direction=LOWER_IS_HIGHER: 1 is highest priority):
        P1: arr=0, burst=4, priority=3
        P2: arr=1, burst=2, priority=1
        P3: arr=2, burst=3, priority=2

    Non-Preemptive Expectation:
        P1 runs [0..4] (C=4, TAT=4, WT=0, RT=0)
        At t=4: P2(prio 1) vs P3(prio 2) -> P2 runs [4..6] (C=6, TAT=5, WT=3, RT=3)
        At t=6: P3 runs [6..9] (C=9, TAT=7, WT=4, RT=4)
        Avg WT = (0 + 3 + 4) / 3 = 7 / 3 = 2.3333

    Preemptive Expectation:
        t=0: P1 starts [0..1]
        t=1: P2(prio 1 < 3) arrives -> P1 preempted! P2 runs [1..3] (C=3, TAT=2, WT=0, RT=0)
        t=3: P3(prio 2 < 3) runs [3..6] (C=6, TAT=4, WT=1, RT=1)
        t=6: P1 resumes for remaining 3 units [6..9] (C=9, TAT=9, WT=5, RT=0)
        Avg WT = (5 + 0 + 1) / 3 = 6 / 3 = 2.0
    """
    procs = [
        Process(process_id="P1", arrival_time=0.0, burst_time=4.0, priority=3),
        Process(process_id="P2", arrival_time=1.0, burst_time=2.0, priority=1),
        Process(process_id="P3", arrival_time=2.0, burst_time=3.0, priority=2),
    ]

    # 1. Non-preemptive run
    res_np = ProcessSchedulerSimulator.simulate(
        processes=procs,
        algorithm_type=AlgorithmType.PRIORITY_NON_PREEMPTIVE,
        direction=PriorityDirection.LOWER_IS_HIGHER,
    )
    p_np = {p.process_id: p for p in res_np.processes}
    assert p_np["P1"].completion_time == 4.0
    assert p_np["P2"].completion_time == 6.0
    assert p_np["P3"].completion_time == 9.0
    assert round(res_np.metrics.average_waiting_time, 4) == round(7.0 / 3.0, 4)

    # 2. Preemptive run
    res_p = ProcessSchedulerSimulator.simulate(
        processes=procs,
        algorithm_type=AlgorithmType.PRIORITY_PREEMPTIVE,
        direction=PriorityDirection.LOWER_IS_HIGHER,
    )
    p_p = {p.process_id: p for p in res_p.processes}
    assert p_p["P2"].completion_time == 3.0
    assert p_p["P3"].completion_time == 6.0
    assert p_p["P1"].completion_time == 9.0
    assert res_p.metrics.average_waiting_time == 2.0


# -----------------------------------------------------------------------------
# 6. Priority Aging Verification
# -----------------------------------------------------------------------------
def test_priority_aging_resolves_starvation():
    """Verify that priority aging incrementally improves waiting processes' priority."""
    # Low priority job arrives early, flooded by high priority jobs
    procs = [
        Process(process_id="P_LOW", arrival_time=0.0, burst_time=6.0, priority=10),
        Process(process_id="P_HI_1", arrival_time=0.0, burst_time=3.0, priority=1),
        Process(process_id="P_HI_2", arrival_time=0.0, burst_time=3.0, priority=1),
        Process(process_id="P_HI_3", arrival_time=0.0, burst_time=3.0, priority=1),
    ]

    # Without aging: P_LOW runs last at t=9
    res_no_aging = ProcessSchedulerSimulator.simulate(
        processes=procs,
        algorithm_type=AlgorithmType.PRIORITY_NON_PREEMPTIVE,
        direction=PriorityDirection.LOWER_IS_HIGHER,
        enable_aging=False,
    )
    p_no_age = {p.process_id: p for p in res_no_aging.processes}
    assert p_no_age["P_LOW"].start_time == 9.0

    # With aging (aging_interval=2.0): P_LOW ages while P_HI_1 and P_HI_2 run
    res_aging = ProcessSchedulerSimulator.simulate(
        processes=procs,
        algorithm_type=AlgorithmType.PRIORITY_NON_PREEMPTIVE,
        direction=PriorityDirection.LOWER_IS_HIGHER,
        enable_aging=True,
        aging_interval=2.0,
    )
    p_age = {p.process_id: p for p in res_aging.processes}
    # Priority should have improved (decreased numeric value)
    assert p_age["P_LOW"].current_priority < p_no_age["P_LOW"].priority


# -----------------------------------------------------------------------------
# 7. Hand-Calculated Test Case: Round Robin
# -----------------------------------------------------------------------------
def test_hand_calculated_round_robin():
    """Verify hand-calculated Round Robin with time quantum = 2.

    Workload:
        P1: arr=0, burst=5
        P2: arr=1, burst=3
        P3: arr=2, burst=1

    Hand-calculated expectation (quantum=2):
        t=0..2: P1 runs (rem 3). P2 (arr=1) and P3 (arr=2) arrive.
                Ready queue: [P2, P3, P1]
        t=2..4: P2 runs (rem 1). Ready queue: [P3, P1, P2]
        t=4..5: P3 runs (burst 1 < 2 -> completes!). (C=5, TAT=3, WT=2, RT=2).
                Ready queue: [P1, P2]
        t=5..7: P1 runs (rem 1). Ready queue: [P2, P1]
        t=7..8: P2 runs (burst 1 < 2 -> completes!). (C=8, TAT=7, WT=4, RT=1).
                Ready queue: [P1]
        t=8..9: P1 runs (burst 1 < 2 -> completes!). (C=9, TAT=9, WT=4, RT=0).

        Avg TAT = (9 + 7 + 3) / 3 = 19 / 3 = 6.3333
        Avg WT  = (4 + 4 + 2) / 3 = 10 / 3 = 3.3333
        Avg RT  = (0 + 1 + 2) / 3 = 3 / 3 = 1.0
        Total simulation time = 9.0
    """
    procs = [
        Process(process_id="P1", arrival_time=0.0, burst_time=5.0),
        Process(process_id="P2", arrival_time=1.0, burst_time=3.0),
        Process(process_id="P3", arrival_time=2.0, burst_time=1.0),
    ]

    result = ProcessSchedulerSimulator.simulate(
        processes=procs,
        algorithm_type=AlgorithmType.ROUND_ROBIN,
        time_quantum=2.0,
    )

    p_map = {p.process_id: p for p in result.processes}
    assert p_map["P3"].completion_time == 5.0
    assert p_map["P2"].completion_time == 8.0
    assert p_map["P1"].completion_time == 9.0

    assert p_map["P1"].start_time == 0.0
    assert p_map["P2"].start_time == 2.0
    assert p_map["P3"].start_time == 4.0

    m = result.metrics
    assert m.total_simulation_time == 9.0
    assert round(m.average_turnaround_time, 4) == round(19.0 / 3.0, 4)
    assert round(m.average_waiting_time, 4) == round(10.0 / 3.0, 4)
    assert m.average_response_time == 1.0


# -----------------------------------------------------------------------------
# 8. Context-Switch Overhead Verification
# -----------------------------------------------------------------------------
def test_context_switch_overhead_calculation():
    """Verify that context-switch overhead inserts dedicated blocks and reduces CPU utilization.

    Workload: P1 (burst 2), P2 (burst 2) both arriving at t=0. Overhead = 0.5.
    Expectation:
        P1 runs [0..2]
        Context switch block [2..2.5]
        P2 runs [2.5..4.5]
        Total time = 4.5, Busy time = 4.0, CS time = 0.5
        CPU utilization = (4.0 / 4.5) * 100 = 88.89%
        Context switches count = 1
    """
    procs = [
        Process(process_id="P1", arrival_time=0.0, burst_time=2.0),
        Process(process_id="P2", arrival_time=0.0, burst_time=2.0),
    ]

    result = ProcessSchedulerSimulator.simulate(
        processes=procs,
        algorithm_type=AlgorithmType.FCFS,
        context_switch_overhead=0.5,
    )

    m = result.metrics
    assert m.total_simulation_time == 4.5
    assert m.busy_cpu_time == 4.0
    assert m.context_switch_time == 0.5
    assert m.context_switches == 1
    assert round(m.cpu_utilization_pct, 2) == 88.89

    cs_blocks = [b for b in result.timeline.blocks if b.block_type == BlockType.CONTEXT_SWITCH]
    assert len(cs_blocks) == 1
    assert cs_blocks[0].start_time == 2.0
    assert cs_blocks[0].end_time == 2.5


# -----------------------------------------------------------------------------
# 9. Algorithm Comparison Mode
# -----------------------------------------------------------------------------
def test_algorithm_comparison_all_six():
    """Verify comparison runner executes all 6 algorithms against identical dataset."""
    procs = [
        Process(process_id="P1", arrival_time=0.0, burst_time=6.0, priority=2),
        Process(process_id="P2", arrival_time=1.0, burst_time=4.0, priority=1),
        Process(process_id="P3", arrival_time=2.0, burst_time=2.0, priority=3),
    ]

    results, rows = compare_all_algorithms(
        processes=procs,
        time_quantum=2.0,
    )

    assert len(results) == 6
    assert len(rows) == 6

    algo_names = [r.algorithm_type for r in rows]
    assert "fcfs" in algo_names
    assert "sjf" in algo_names
    assert "srtf" in algo_names
    assert "priority_non_preemptive" in algo_names
    assert "priority_preemptive" in algo_names
    assert "round_robin" in algo_names

    # Verify rows contain populated metrics
    for r in rows:
        assert r.average_turnaround_time > 0.0
        assert r.average_waiting_time >= 0.0
        assert r.cpu_utilization_pct > 0.0
        assert r.total_simulation_time > 0.0


# -----------------------------------------------------------------------------
# 10. Workload Presets Integrity
# -----------------------------------------------------------------------------
def test_workload_presets_all_valid():
    """Verify that all 7 educational presets load, validate, and execute cleanly."""
    presets = get_all_presets()
    assert len(presets) == 7

    preset_ids = [p.preset_id for p in presets]
    assert "simple_varying_bursts" in preset_ids
    assert "staggered_arrivals" in preset_ids
    assert "sjf_benchmark" in preset_ids
    assert "priority_demo" in preset_ids
    assert "round_robin_preemption" in preset_ids
    assert "starvation_aging" in preset_ids
    assert "cpu_idle_intervals" in preset_ids

    # Every preset must pass validation and simulate cleanly
    for p in presets:
        procs = p.get_cloned_processes()
        validate_process_list(procs)
        res = ProcessSchedulerSimulator.simulate(procs, AlgorithmType.FCFS)
        assert res.metrics.completed_processes == len(procs)

    # Test retrieval by ID
    p1 = get_preset_by_id("sjf_benchmark")
    assert p1.preset_id == "sjf_benchmark"
    with pytest.raises(KeyError):
        get_preset_by_id("non_existent_preset")

