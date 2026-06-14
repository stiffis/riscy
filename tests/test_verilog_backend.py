from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from riscy.verilog_backend import DEFAULT_LIB, VerilogPipelineCPU

HDL = Path(__file__).resolve().parent.parent / "hdl"
PROGRAM = HDL / "riscvtest_base.txt"


def load_words(path: Path) -> list[int]:
    return [int(line.strip(), 16) for line in path.read_text().splitlines() if line.strip()]


@unittest.skipUnless(DEFAULT_LIB.exists(), "Verilator library not built (run: make -C hdl)")
class VerilogPipelineTests(unittest.TestCase):
    def test_base_program_matches_hardware_expectations(self) -> None:
        cpu = VerilogPipelineCPU(load_words(PROGRAM))
        for _ in range(120):
            cpu.step()
        expected = {96: 7, 100: 14, 104: 15, 108: 7, 112: 1, 116: 1}
        for addr, value in expected.items():
            self.assertEqual(cpu.memory.get(addr, 0), value, f"Mem[{addr}]")

    def test_shadow_pipeline_matches_hardware(self) -> None:
        cpu = VerilogPipelineCPU(load_words(PROGRAM))
        for _ in range(40):
            cpu.step()
            stages = cpu.pipeline_stages()
            id_pc, id_instr = stages[1][1], stages[1][2]
            if id_pc is not None:
                self.assertEqual(id_instr, cpu._lib.sim_instr_d(cpu._handle), "ID instr")
                self.assertEqual(id_pc, cpu._lib.sim_pc_d(cpu._handle), "ID pc")
            ex_pc = stages[2][1]
            if ex_pc is not None:
                self.assertEqual(ex_pc, cpu._lib.sim_pc_e(cpu._handle), "EX pc")

    def test_reset_clears_state(self) -> None:
        cpu = VerilogPipelineCPU(load_words(PROGRAM))
        for _ in range(120):
            cpu.step()
        cpu.reset()
        self.assertEqual(cpu.pc, 0)
        self.assertEqual(cpu.registers, [0] * 32)
        self.assertEqual(cpu.memory, {})
        self.assertEqual(cpu.step_count, 0)


if __name__ == "__main__":
    unittest.main()
