from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from riscy.reference_cpu import DEFAULT_SP, to_signed32
from riscy.single_cycle_cpu import SingleCycleCPU


def i_type(op, f3, rd, rs1, imm):
    return ((imm & 0xFFF) << 20) | ((rs1 & 0x1F) << 15) | ((f3 & 7) << 12) | ((rd & 0x1F) << 7) | (op & 0x7F)


def s_type(op, f3, rs1, rs2, imm):
    imm &= 0xFFF
    return ((imm >> 5) << 25) | ((rs2 & 0x1F) << 20) | ((rs1 & 0x1F) << 15) | ((f3 & 7) << 12) | ((imm & 0x1F) << 7) | (op & 0x7F)


def r_type(op, f3, f7, rd, rs1, rs2):
    return ((f7 & 0x7F) << 25) | ((rs2 & 0x1F) << 20) | ((rs1 & 0x1F) << 15) | ((f3 & 7) << 12) | ((rd & 0x1F) << 7) | (op & 0x7F)


def u_type(op, rd, imm20):
    return ((imm20 & 0xFFFFF) << 12) | ((rd & 0x1F) << 7) | (op & 0x7F)


def b_type(op, f3, rs1, rs2, imm):
    i = imm & 0x1FFF
    return (
        (((i >> 12) & 1) << 31)
        | (((i >> 5) & 0x3F) << 25)
        | ((rs2 & 0x1F) << 20)
        | ((rs1 & 0x1F) << 15)
        | ((f3 & 7) << 12)
        | (((i >> 1) & 0xF) << 8)
        | (((i >> 11) & 1) << 7)
        | (op & 0x7F)
    )


def addi(rd, rs1, imm):
    return i_type(0x13, 0x0, rd, rs1, imm)


def lui(rd, imm20):
    return u_type(0x37, rd, imm20)


def run(words, steps=64):
    cpu = SingleCycleCPU(words)
    cpu.run(steps)
    return cpu


class MemoryModelTests(unittest.TestCase):
    def test_sp_initialized(self) -> None:
        cpu = SingleCycleCPU([])
        self.assertEqual(cpu.registers[2], DEFAULT_SP)

    def test_word_is_little_endian(self) -> None:
        # x1 = 0x12345678 ; sw x1, 0(x0)
        cpu = run([lui(1, 0x12345), addi(1, 1, 0x678), s_type(0x23, 0x2, 0, 1, 0)])
        self.assertEqual(cpu.read_byte(0), 0x78)
        self.assertEqual(cpu.read_byte(1), 0x56)
        self.assertEqual(cpu.read_byte(2), 0x34)
        self.assertEqual(cpu.read_byte(3), 0x12)
        self.assertEqual(cpu.read_word(0), 0x12345678)

    def test_sb_writes_one_byte(self) -> None:
        # x1 = -1 ; sw x1,0(x0) ; sb x0,0(x0)  -> only byte 0 cleared
        cpu = run([addi(1, 0, -1), s_type(0x23, 0x2, 0, 1, 0), s_type(0x23, 0x0, 0, 0, 0)])
        self.assertEqual(cpu.read_word(0), 0xFFFFFF00)
        self.assertEqual(cpu.read_byte(0), 0x00)


class LoadTests(unittest.TestCase):
    def test_lb_sign_extend_vs_lbu(self) -> None:
        # x1 = 0x80 ; sb x1,0(x0) ; lb x2,0(x0) ; lbu x3,0(x0)
        cpu = run([addi(1, 0, 0x80), s_type(0x23, 0x0, 0, 1, 0),
                   i_type(0x03, 0x0, 2, 0, 0), i_type(0x03, 0x4, 3, 0, 0)])
        self.assertEqual(cpu.registers[2], 0xFFFFFF80)
        self.assertEqual(cpu.registers[3], 0x00000080)

    def test_lh_sign_extend_vs_lhu(self) -> None:
        # x1 = 0x8000 ; sh x1,0(x0) ; lh x2,0(x0) ; lhu x3,0(x0)
        cpu = run([lui(1, 0x8), s_type(0x23, 0x1, 0, 1, 0),
                   i_type(0x03, 0x1, 2, 0, 0), i_type(0x03, 0x5, 3, 0, 0)])
        self.assertEqual(cpu.registers[2], 0xFFFF8000)
        self.assertEqual(cpu.registers[3], 0x00008000)


class UnsignedCompareTests(unittest.TestCase):
    def test_sltu_vs_slt(self) -> None:
        # x1=-1 (0xFFFFFFFF), x2=1 ; sltu x3,x1,x2 ; slt x4,x1,x2
        cpu = run([addi(1, 0, -1), addi(2, 0, 1),
                   r_type(0x33, 0x3, 0x00, 3, 1, 2), r_type(0x33, 0x2, 0x00, 4, 1, 2)])
        self.assertEqual(cpu.registers[3], 0)  # unsigned: 0xFFFFFFFF < 1 is false
        self.assertEqual(cpu.registers[4], 1)  # signed: -1 < 1 is true

    def test_sltiu(self) -> None:
        # x1=-1 ; sltiu x2,x1,1 ; slti x3,x1,1
        cpu = run([addi(1, 0, -1), i_type(0x13, 0x3, 2, 1, 1), i_type(0x13, 0x2, 3, 1, 1)])
        self.assertEqual(cpu.registers[2], 0)
        self.assertEqual(cpu.registers[3], 1)


class UpperAndBranchTests(unittest.TestCase):
    def test_auipc(self) -> None:
        # nop ; auipc x1, 0x1  (at pc=4 -> x1 = 4 + 0x1000)
        cpu = run([addi(0, 0, 0), u_type(0x17, 1, 0x1)])
        self.assertEqual(cpu.registers[1], 0x4 + 0x1000)

    def test_bltu_taken_when_slt_not(self) -> None:
        # x1=1, x2=-1 ; bltu x1,x2,+8 (1<0xFFFFFFFF -> taken) ; addi x3,x0,5 (skip) ; addi x4,x0,7
        cpu = run([addi(1, 0, 1), addi(2, 0, -1), b_type(0x63, 0x6, 1, 2, 8),
                   addi(3, 0, 5), addi(4, 0, 7)])
        self.assertEqual(cpu.registers[3], 0)
        self.assertEqual(cpu.registers[4], 7)

    def test_bgeu_taken(self) -> None:
        # x1=-1, x2=1 ; bgeu x1,x2,+8 (0xFFFFFFFF>=1 -> taken) ; addi x3,x0,5 (skip) ; addi x4,x0,7
        cpu = run([addi(1, 0, -1), addi(2, 0, 1), b_type(0x63, 0x7, 1, 2, 8),
                   addi(3, 0, 5), addi(4, 0, 7)])
        self.assertEqual(cpu.registers[3], 0)
        self.assertEqual(cpu.registers[4], 7)


if __name__ == "__main__":
    unittest.main()
