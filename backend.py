from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class StepResult:
    pc_before: int
    instruction: int
    disasm: str
    changed_registers: list[int] = field(default_factory=list)
    changed_memory: list[int] = field(default_factory=list)
    events: list[str] = field(default_factory=list)


class CPUBackend(ABC):
    model_name = "abstract"

    pc: int
    registers: list[int]
    memory: dict[int, int]
    step_count: int
    halted: bool
    last_result: StepResult

    def __init__(self) -> None:
        self.breakpoints: set[int] = set()

    @abstractmethod
    def reset(self) -> None:
        ...

    @abstractmethod
    def step(self) -> StepResult:
        ...

    def instruction_at(self, addr: int) -> int:
        return self.memory.get(addr, 0)

    def data_word(self, addr: int) -> int:
        return self.memory.get(addr, 0)

    def run(self, steps: int) -> list[StepResult]:
        results = []
        for _ in range(steps):
            if self.halted:
                break
            results.append(self.step())
        return results

    def toggle_breakpoint(self, addr: int) -> bool:
        if addr in self.breakpoints:
            self.breakpoints.discard(addr)
            return False
        self.breakpoints.add(addr)
        return True

    def continue_run(self, max_steps: int = 100_000) -> list[StepResult]:
        results = []
        for _ in range(max_steps):
            if self.halted:
                break
            results.append(self.step())
            if self.pc in self.breakpoints:
                break
        return results

    def run_to_end(self, max_steps: int = 100_000) -> list[StepResult]:
        results = []
        for _ in range(max_steps):
            if self.halted:
                break
            results.append(self.step())
        return results

    def run_to_address(self, addr: int, max_steps: int = 100_000) -> list[StepResult]:
        results = []
        for _ in range(max_steps):
            if self.halted:
                break
            results.append(self.step())
            if self.pc == addr:
                break
        return results
