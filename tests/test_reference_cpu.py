
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from riscy.reference_cpu import to_signed32
from riscy.single_cycle_cpu import SingleCycleCPU


def run(words: list[int], steps: int = 64) -> SingleCycleCPU:
    cpu = SingleCycleCPU(words)
    cpu.run(steps)
    return cpu


class ImmediateTests(unittest.TestCase):
    def test_addi(self) -> None:
        cpu = run([0x00500093])
        self.assertEqual(cpu.registers[1], 5)

    def test_addi_negative(self) -> None:
        cpu = run([0xFFF00093])
        self.assertEqual(cpu.registers[1], 0xFFFFFFFF)

    def test_andi_ori_xori(self) -> None:
        cpu = run([0x0F000093, 0x00F0F113, 0x00F0E193, 0x0FF0C213])
        self.assertEqual(cpu.registers[2], 0x00)
        self.assertEqual(cpu.registers[3], 0xFF)
        self.assertEqual(cpu.registers[4], 0x0F)

    def test_slti(self) -> None:
        cpu = run([0xFFF00093, 0x0000A113])
        self.assertEqual(cpu.registers[2], 1)

    def test_shift_immediates(self) -> None:
        cpu = run([0xFF800093, 0x00109113, 0x0010D193, 0x4010D213])
        self.assertEqual(cpu.registers[2], (0xFFFFFFF8 << 1) & 0xFFFFFFFF)
        self.assertEqual(cpu.registers[3], 0xFFFFFFF8 >> 1)
        self.assertEqual(to_signed32(cpu.registers[4]), -4)


class RTypeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.prologue = [0x00A00093, 0x00300113]

    def test_add_sub(self) -> None:
        cpu = run(self.prologue + [0x002081B3, 0x40208233])
        self.assertEqual(cpu.registers[3], 13)
        self.assertEqual(cpu.registers[4], 7)

    def test_logical(self) -> None:
        cpu = run(self.prologue + [0x0020F1B3, 0x0020E233, 0x0020C2B3])
        self.assertEqual(cpu.registers[3], 10 & 3)
        self.assertEqual(cpu.registers[4], 10 | 3)
        self.assertEqual(cpu.registers[5], 10 ^ 3)

    def test_slt_signed(self) -> None:
        cpu = run([0xFFF00093, 0x00100113, 0x0020A1B3])
        self.assertEqual(cpu.registers[3], 1)

    def test_shifts(self) -> None:
        cpu = run([0xFF800093, 0x00100113, 0x002091B3, 0x0020D233, 0x4020D2B3])
        self.assertEqual(cpu.registers[3], (0xFFFFFFF8 << 1) & 0xFFFFFFFF)
        self.assertEqual(cpu.registers[4], 0xFFFFFFF8 >> 1)
        self.assertEqual(to_signed32(cpu.registers[5]), -4)


class MemoryTests(unittest.TestCase):
    def test_store_then_load(self) -> None:
        cpu = run([0x02A00093, 0x04102023, 0x04002103])
        self.assertEqual(cpu.memory[0x40], 42)
        self.assertEqual(cpu.registers[2], 42)


class BranchTests(unittest.TestCase):
    def test_beq_taken_skips(self) -> None:
        cpu = run([0x00000463, 0x00100093, 0x00200113])
        self.assertEqual(cpu.registers[1], 0)
        self.assertEqual(cpu.registers[2], 2)

    def test_bne_not_taken_falls_through(self) -> None:
        cpu = run([0x00001463, 0x00100093, 0x00200113])
        self.assertEqual(cpu.registers[1], 1)
        self.assertEqual(cpu.registers[2], 2)


class UpperAndJumpTests(unittest.TestCase):
    def test_lui(self) -> None:
        cpu = run([0x123450B7])
        self.assertEqual(cpu.registers[1], 0x12345000)

    def test_jal_sets_link_and_jumps(self) -> None:
        cpu = run([0x008000EF, 0x00100113, 0x00300193])
        self.assertEqual(cpu.registers[1], 4)
        self.assertEqual(cpu.registers[2], 0)
        self.assertEqual(cpu.registers[3], 3)

    def test_jalr(self) -> None:
        cpu = run([0x00C00093, 0x00008167, 0x00100193, 0x00400213])
        self.assertEqual(cpu.registers[2], 8)
        self.assertEqual(cpu.registers[3], 0)
        self.assertEqual(cpu.registers[4], 4)


class RegZeroTests(unittest.TestCase):
    def test_x0_stays_zero(self) -> None:
        cpu = run([0x00500013])
        self.assertEqual(cpu.registers[0], 0)


class HaltTests(unittest.TestCase):
    def test_end_of_program(self) -> None:
        cpu = run([0x00500093])
        self.assertTrue(cpu.halted)
        self.assertIn("end of program", cpu.last_result.events[-1])

    def test_zero_between_instructions_is_illegal(self) -> None:
        cpu = run([0x00100093, 0x00000000, 0x00200113])
        self.assertTrue(cpu.halted)
        self.assertIn("Illegal", cpu.last_result.events[-1])
        self.assertEqual(cpu.registers[2], 0)

    def test_nop_is_not_halt(self) -> None:
        cpu = run([0x00000013, 0x00700093])
        self.assertEqual(cpu.registers[1], 7)


class BreakpointTests(unittest.TestCase):
    PROGRAM = [0x00100093, 0x00200113, 0x00300193, 0x00400213]

    def test_toggle_returns_state(self) -> None:
        cpu = SingleCycleCPU(self.PROGRAM)
        self.assertTrue(cpu.toggle_breakpoint(0x8))
        self.assertIn(0x8, cpu.breakpoints)
        self.assertFalse(cpu.toggle_breakpoint(0x8))
        self.assertNotIn(0x8, cpu.breakpoints)

    def test_continue_stops_before_breakpoint(self) -> None:
        cpu = SingleCycleCPU(self.PROGRAM)
        cpu.toggle_breakpoint(0x8)
        cpu.continue_run()
        self.assertEqual(cpu.pc, 0x8)
        self.assertEqual(cpu.registers[1], 1)
        self.assertEqual(cpu.registers[2], 2)
        self.assertEqual(cpu.registers[3], 0)
        self.assertFalse(cpu.halted)

    def test_continue_without_breakpoint_runs_to_end(self) -> None:
        cpu = SingleCycleCPU(self.PROGRAM)
        cpu.continue_run()
        self.assertTrue(cpu.halted)
        self.assertEqual(cpu.registers[4], 4)

    def test_run_to_end(self) -> None:
        cpu = SingleCycleCPU(self.PROGRAM)
        cpu.run_to_end()
        self.assertTrue(cpu.halted)
        self.assertEqual(cpu.registers[4], 4)

    def test_run_to_end_ignores_breakpoints(self) -> None:
        cpu = SingleCycleCPU(self.PROGRAM)
        cpu.toggle_breakpoint(0x8)
        cpu.run_to_end()
        self.assertTrue(cpu.halted)
        self.assertEqual(cpu.registers[4], 4)

    def test_run_to_address(self) -> None:
        cpu = SingleCycleCPU(self.PROGRAM)
        cpu.run_to_address(0xC)
        self.assertEqual(cpu.pc, 0xC)
        self.assertEqual(cpu.registers[3], 3)
        self.assertEqual(cpu.registers[4], 0)
        self.assertFalse(cpu.halted)

    def test_safety_limit_on_infinite_loop(self) -> None:
        cpu = SingleCycleCPU([0x0000006F])
        results = cpu.run_to_end(max_steps=50)
        self.assertEqual(len(results), 50)
        self.assertFalse(cpu.halted)


if __name__ == "__main__":
    unittest.main()
