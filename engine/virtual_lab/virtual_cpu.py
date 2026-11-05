"""Virtual Multicore Processor model and configuration."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from engine.virtual_lab.virtual_core import VirtualCore, VirtualCoreState, VirtualCoreType
from engine.virtual_lab.virtual_task import VirtualTask


@dataclass
class VirtualCPUConfig:
    """User-defined configuration for a simulated virtual multicore CPU."""
    name: str = "Virtual CoreSync-X16"
    physical_cores: int = 8
    logical_threads: int = 16
    enable_hybrid: bool = False
    p_core_count: int = 4
    e_core_count: int = 8
    p_core_speed: float = 1.5
    e_core_speed: float = 0.8
    standard_speed: float = 1.0


class VirtualCPU:
    """Simulated multicore CPU containing an arbitrary number of virtual execution cores."""

    def __init__(self, config: Optional[VirtualCPUConfig] = None):
        self.config = config or VirtualCPUConfig()
        self.cores: Dict[int, VirtualCore] = {}
        self.current_tick: int = 0
        self._build_cores()

    def _build_cores(self) -> None:
        """Construct virtual cores according to config."""
        self.cores.clear()
        total_cores = max(1, min(self.config.logical_threads, 256))

        if self.config.enable_hybrid:
            p_count = min(self.config.p_core_count, total_cores)
            e_count = min(self.config.e_core_count, total_cores - p_count)

            # Assign P-cores
            for i in range(p_count):
                self.cores[i] = VirtualCore(
                    core_id=i,
                    core_type=VirtualCoreType.PERFORMANCE,
                    speed_multiplier=self.config.p_core_speed,
                )
            # Assign E-cores
            for j in range(p_count, p_count + e_count):
                self.cores[j] = VirtualCore(
                    core_id=j,
                    core_type=VirtualCoreType.EFFICIENCY,
                    speed_multiplier=self.config.e_core_speed,
                )
            # Remaining standard cores if any
            for k in range(p_count + e_count, total_cores):
                self.cores[k] = VirtualCore(
                    core_id=k,
                    core_type=VirtualCoreType.STANDARD,
                    speed_multiplier=self.config.standard_speed,
                )
        else:
            for i in range(total_cores):
                self.cores[i] = VirtualCore(
                    core_id=i,
                    core_type=VirtualCoreType.STANDARD,
                    speed_multiplier=self.config.standard_speed,
                )

    def reconfigure(self, config: VirtualCPUConfig) -> None:
        """Apply new configuration and rebuild cores."""
        self.config = config
        self.current_tick = 0
        self._build_cores()

    def step(self, tick_delta: int = 1) -> List[VirtualTask]:
        """Advance simulation clock by tick_delta across all virtual cores.

        Returns:
            List of tasks completed during this tick step.
        """
        self.current_tick += tick_delta
        completed: List[VirtualTask] = []

        for core in self.cores.values():
            finished = core.step(tick_delta=tick_delta, current_tick=self.current_tick)
            if finished:
                completed.append(finished)

        return completed

    def get_idle_cores(self) -> List[VirtualCore]:
        """Return list of currently idle virtual cores."""
        return [c for c in self.cores.values() if c.state == VirtualCoreState.IDLE]

    @property
    def overall_simulated_utilization(self) -> float:
        """Compute aggregate virtual CPU utilization across all virtual cores."""
        if not self.cores:
            return 0.0
        return sum(c.simulated_utilization for c in self.cores.values()) / len(self.cores)

    @property
    def core_count(self) -> int:
        return len(self.cores)

    def reset_metrics(self) -> None:
        """Reset execution counters and tick state."""
        self.current_tick = 0
        for core in self.cores.values():
            core.state = VirtualCoreState.IDLE
            core.current_task = None
            core.busy_ticks = 0
            core.total_ticks = 0
            core.simulated_utilization = 0.0

