from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from riscy.asm_loader import load_program
from riscy.single_cycle_cpu import SingleCycleCPU

PROGRAMS = Path(__file__).resolve().parent / "programs"


def run_until_done(cpu: SingleCycleCPU, max_steps: int = 300000) -> None:
    for _ in range(max_steps):
        pc = cpu.pc
        cpu.step()
        if cpu.halted or cpu.pc == pc:
            return


def load(name: str) -> SingleCycleCPU:
    return SingleCycleCPU(load_program(str(PROGRAMS / name)).words)


@unittest.skipUnless((PROGRAMS / "riscvtest.bin").exists(), "compiled programs not built (run tests/programs/build.sh)")
class CompiledProgramTests(unittest.TestCase):
    def test_riscvtest(self) -> None:
        cpu = load("riscvtest.bin")
        run_until_done(cpu)
        self.assertEqual(cpu.read_word(96), 7)
        self.assertEqual(cpu.read_word(100), 25)

    def test_symmetric_tree(self) -> None:
        cpu = load("tree.bin")
        run_until_done(cpu)
        self.assertEqual(cpu.registers[10], 1)

    def test_quicksort(self) -> None:
        cpu = load("quicksort.bin")
        run_until_done(cpu)
        result = [cpu.read_word(0x1000 + i * 4) for i in range(7)]
        self.assertEqual(result, [1, 2, 3, 4, 6, 8, 9])


if __name__ == "__main__":
    unittest.main()
