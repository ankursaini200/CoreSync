"""Unit and integration tests for Virtual Lab multicore simulation engine."""

import pytest

from engine.virtual_lab.virtual_core import VirtualCore, VirtualCoreState, VirtualCoreType
from engine.virtual_lab.virtual_cpu import VirtualCPU, VirtualCPUConfig
from engine.virtual_lab.virtual_task import TaskPriority, TaskState, VirtualTask
from engine.virtual_lab.virtual_scheduler import SchedulingAlgorithm, VirtualScheduler
from engine.virtual_lab.workload_generator import VirtualWorkloadGenerator


def test_virtual_cpu_homogeneous_creation():
    """Verify homogeneous virtual CPU configuration and core counts."""
    cfg = VirtualCPUConfig(
        name="Virtual Test-16",
        physical_cores=8,
        logical_threads=16,
        enable_hybrid=False,
        standard_speed=1.0,
    )
    vcpu = VirtualCPU(cfg)

    assert len(vcpu.cores) == 16
    for core in vcpu.cores.values():
        assert core.core_type == VirtualCoreType.STANDARD
        assert core.speed_multiplier == 1.0
        assert core.state == VirtualCoreState.IDLE


def test_virtual_cpu_hybrid_creation():
    """Verify hybrid heterogeneous virtual CPU configuration with P and E cores."""
    cfg = VirtualCPUConfig(
        name="Virtual Hybrid-12",
        physical_cores=8,
        logical_threads=12,
        enable_hybrid=True,
        p_core_count=4,
        e_core_count=8,
        p_core_speed=1.5,
        e_core_speed=0.8,
    )
    vcpu = VirtualCPU(cfg)

    assert len(vcpu.cores) == 12
    p_cores = [c for c in vcpu.cores.values() if c.core_type == VirtualCoreType.PERFORMANCE]
    e_cores = [c for c in vcpu.cores.values() if c.core_type == VirtualCoreType.EFFICIENCY]

    assert len(p_cores) == 4
    assert len(e_cores) == 8
    assert p_cores[0].speed_multiplier == 1.5
    assert e_cores[0].speed_multiplier == 0.8


def test_virtual_workload_generator():
    """Verify synthetic batch generation."""
    tasks = VirtualWorkloadGenerator.generate_batch(count=10, burst_range=(15, 30))
    assert len(tasks) == 10
    for t in tasks:
        assert isinstance(t, VirtualTask)
        assert 15 <= t.burst_ticks <= 30
        assert t.remaining_ticks == t.burst_ticks
        assert t.state == TaskState.READY


def test_virtual_scheduler_fcfs():
    """Verify First-Come-First-Served task dispatch and completion."""
    vcpu = VirtualCPU(VirtualCPUConfig(logical_threads=2, standard_speed=1.0))
    scheduler = VirtualScheduler(vcpu, algorithm=SchedulingAlgorithm.FCFS)

    task1 = VirtualTask(task_id=1, name="T1", burst_ticks=10)
    task2 = VirtualTask(task_id=2, name="T2", burst_ticks=20)
    task3 = VirtualTask(task_id=3, name="T3", burst_ticks=10)

    scheduler.submit_batch([task1, task2, task3])
    scheduler.dispatch()

    # Cores 0 and 1 should have task 1 and task 2
    assert vcpu.cores[0].state == VirtualCoreState.BUSY
    assert vcpu.cores[1].state == VirtualCoreState.BUSY
    assert len(scheduler.ready_queue) == 1

    # Step 10 ticks: task 1 should finish, task 3 dispatched to core 0
    completed = scheduler.step(10)
    assert len(completed) >= 1
    assert task1 in scheduler.completed_tasks
    assert task1.turnaround_ticks == 10
    assert task1.waiting_ticks == 0

    # Step 10 more ticks: task 3 and task 2 should finish
    completed2 = scheduler.step(10)
    assert len(scheduler.completed_tasks) == 3
    assert scheduler.avg_waiting_time >= 0.0
    assert scheduler.avg_turnaround_time > 0.0


def test_virtual_scheduler_priority():
    """Verify priority-based ordering in ready queue."""
    vcpu = VirtualCPU(VirtualCPUConfig(logical_threads=1, standard_speed=1.0))
    scheduler = VirtualScheduler(vcpu, algorithm=SchedulingAlgorithm.PRIORITY)

    task_low = VirtualTask(task_id=1, name="Low", burst_ticks=10, priority=TaskPriority.LOW)
    task_high = VirtualTask(task_id=2, name="High", burst_ticks=10, priority=TaskPriority.HIGH)
    task_med = VirtualTask(task_id=3, name="Med", burst_ticks=10, priority=TaskPriority.MEDIUM)

    scheduler.submit_batch([task_low, task_high, task_med])

    # With Priority policy, ready queue should be High, Medium, Low
    queue_order = [t.name for t in scheduler.ready_queue]
    assert queue_order == ["High", "Med", "Low"]

    scheduler.dispatch()
    assert vcpu.cores[0].current_task.name == "High"


def test_virtual_scheduler_round_robin_preemption():
    """Verify Round Robin time-quantum preemption."""
    vcpu = VirtualCPU(VirtualCPUConfig(logical_threads=1, standard_speed=1.0))
    scheduler = VirtualScheduler(vcpu, algorithm=SchedulingAlgorithm.ROUND_ROBIN, time_quantum=5)

    task_long = VirtualTask(task_id=1, name="LongTask", burst_ticks=20)
    task_short = VirtualTask(task_id=2, name="ShortTask", burst_ticks=10)

    scheduler.submit_batch([task_long, task_short])
    scheduler.dispatch()

    assert vcpu.cores[0].current_task.name == "LongTask"

    # Step 5 ticks (full quantum)
    scheduler.step(5)

    # LongTask should have been preempted back to queue, ShortTask now on core!
    assert vcpu.cores[0].current_task.name == "ShortTask"
    assert len(scheduler.ready_queue) == 1
    assert scheduler.ready_queue[0].name == "LongTask"


def test_virtual_metrics_independent_of_real_hardware():
    """Verify that virtual CPU utilization is calculated from simulated ticks, not psutil."""
    vcpu = VirtualCPU(VirtualCPUConfig(logical_threads=4, standard_speed=1.0))
    assert vcpu.overall_simulated_utilization == 0.0

    # Assign tasks to all 4 cores
    for i in range(4):
        vcpu.cores[i].assign_task(VirtualTask(task_id=i, name=f"T{i}", burst_ticks=100), current_tick=0)

    # Advance 1 tick
    vcpu.step(1)

    # All cores are busy, so simulated utilization is 100.0%
    assert vcpu.overall_simulated_utilization == 100.0
