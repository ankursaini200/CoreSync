"""Unit tests for Linux CPU list parsing and sysfs topology inspection."""

from pathlib import Path
import pytest

from utils.cpu_topology import (
    CoreType,
    CPUTopology,
    LogicalCPU,
    parse_cpu_list,
    parse_sysfs_topology,
)


def test_parse_cpu_list_ranges():
    """Verify standard range syntax parsing."""
    assert parse_cpu_list("0-3") == [0, 1, 2, 3]
    assert parse_cpu_list("0-0") == [0]
    assert parse_cpu_list("4-7") == [4, 5, 6, 7]


def test_parse_cpu_list_comma_separated():
    """Verify comma-separated lists and single numbers."""
    assert parse_cpu_list("0,2,4") == [0, 2, 4]
    assert parse_cpu_list("12") == [12]


def test_parse_cpu_list_complex():
    """Verify mixed ranges and individual numbers."""
    assert parse_cpu_list("0-3,8-11,14") == [0, 1, 2, 3, 8, 9, 10, 11, 14]
    assert parse_cpu_list("  0-1,  4, 6-7  \n") == [0, 1, 4, 6, 7]


def test_parse_cpu_list_edge_cases():
    """Verify empty and malformed CPU lists do not crash."""
    assert parse_cpu_list("") == []
    assert parse_cpu_list("   ") == []
    assert parse_cpu_list("invalid-range") == []
    assert parse_cpu_list("0,abc,2") == [0, 2]


def test_mock_sysfs_smp_topology(tmp_path: Path):
    """Test deterministic sysfs topology parsing for a standard symmetric 4-core, 8-thread CPU."""
    sysfs_cpu = tmp_path / "sysfs_cpu"
    sysfs_cpu.mkdir(parents=True)
    pmu_dir = tmp_path / "pmu"
    pmu_dir.mkdir(parents=True)

    # Create 8 logical CPUs (4 physical cores, SMT=2)
    # CPU 0 & 1 share core_id 0, CPU 2 & 3 share core_id 1, etc.
    for i in range(8):
        cpu_dir = sysfs_cpu / f"cpu{i}"
        topo_dir = cpu_dir / "topology"
        freq_dir = cpu_dir / "cpufreq"
        topo_dir.mkdir(parents=True)
        freq_dir.mkdir(parents=True)

        phys_core = i // 2
        (topo_dir / "core_id").write_text(str(phys_core))
        (topo_dir / "physical_package_id").write_text("0")

        sibling_a = phys_core * 2
        sibling_b = sibling_a + 1
        (topo_dir / "thread_siblings_list").write_text(f"{sibling_a}-{sibling_b}")

        (freq_dir / "cpuinfo_max_freq").write_text("4000000")
        (freq_dir / "scaling_cur_freq").write_text("3200000")

    topology = parse_sysfs_topology(sysfs_root=str(sysfs_cpu), pmu_root=str(pmu_dir))

    assert topology.logical_cpu_count == 8
    assert topology.physical_core_count == 4
    assert topology.package_count == 1
    assert topology.is_hybrid is False
    assert len(topology.unknown_cores) == 8
    assert len(topology.p_cores) == 0
    assert len(topology.e_cores) == 0

    # Verify SMT relationships
    assert topology.logical_cpus[0].is_smt is True
    assert topology.logical_cpus[0].thread_siblings == [0, 1]
    assert topology.logical_cpus[0].max_freq_mhz == 4000.0
    assert topology.logical_cpus[0].core_type == CoreType.UNKNOWN


def test_mock_sysfs_hybrid_topology(tmp_path: Path):
    """Test deterministic sysfs topology parsing for an Intel Hybrid CPU (P-cores & E-cores)."""
    sysfs_cpu = tmp_path / "sysfs_cpu"
    sysfs_cpu.mkdir(parents=True)
    pmu_dir = tmp_path / "pmu"
    pmu_dir.mkdir(parents=True)

    # Create authoritative PMU event source devices
    core_pmu = pmu_dir / "cpu_core"
    core_pmu.mkdir(parents=True)
    (core_pmu / "cpus").write_text("0-3")

    atom_pmu = pmu_dir / "cpu_atom"
    atom_pmu.mkdir(parents=True)
    (atom_pmu / "cpus").write_text("4-5")

    # Create 6 logical CPUs: 0-3 are P-cores (2 physical cores with SMT), 4-5 are E-cores (single-threaded)
    for i in range(6):
        cpu_dir = sysfs_cpu / f"cpu{i}"
        topo_dir = cpu_dir / "topology"
        freq_dir = cpu_dir / "cpufreq"
        topo_dir.mkdir(parents=True)
        freq_dir.mkdir(parents=True)

        if i < 4:
            # P-cores
            phys_core = i // 2
            (topo_dir / "core_id").write_text(str(phys_core))
            (topo_dir / "physical_package_id").write_text("0")
            sib_a = phys_core * 2
            (topo_dir / "thread_siblings_list").write_text(f"{sib_a}-{sib_a + 1}")
            (freq_dir / "cpuinfo_max_freq").write_text("4800000")
        else:
            # E-cores
            (topo_dir / "core_id").write_text(str(i + 10))
            (topo_dir / "physical_package_id").write_text("0")
            (topo_dir / "thread_siblings_list").write_text(str(i))
            (freq_dir / "cpuinfo_max_freq").write_text("3400000")

    topology = parse_sysfs_topology(sysfs_root=str(sysfs_cpu), pmu_root=str(pmu_dir))

    assert topology.logical_cpu_count == 6
    assert topology.physical_core_count == 4  # 2 P physical + 2 E physical
    assert topology.is_hybrid is True
    assert topology.p_cores == [0, 1, 2, 3]
    assert topology.e_cores == [4, 5]
    assert topology.unknown_cores == []

    # Verify core type enums
    assert topology.logical_cpus[0].core_type == CoreType.PERFORMANCE
    assert topology.logical_cpus[4].core_type == CoreType.EFFICIENCY


def test_missing_and_restricted_sysfs_files(tmp_path: Path):
    """Verify graceful handling when topology files are missing or unreadable."""
    sysfs_cpu = tmp_path / "sysfs_cpu"
    sysfs_cpu.mkdir(parents=True)
    pmu_dir = tmp_path / "pmu"
    pmu_dir.mkdir(parents=True)

    # Empty cpu0 dir without topology or cpufreq subdirectories
    (sysfs_cpu / "cpu0").mkdir()

    topology = parse_sysfs_topology(sysfs_root=str(sysfs_cpu), pmu_root=str(pmu_dir))

    assert topology.logical_cpu_count == 1
    cpu0 = topology.logical_cpus[0]
    assert cpu0.package_id is None
    assert cpu0.core_id is None
    assert cpu0.thread_siblings == [0]
    assert cpu0.is_smt is False
    assert cpu0.max_freq_khz is None
    assert cpu0.core_type == CoreType.UNKNOWN

