#!/usr/bin/env python3
"""Assemble a small RV32I subset into 32-bit hex words.

Supported instructions are the ones currently relevant to the project:
  lw, addi, slli, xori, srli, srai, ori, andi,
  sw, add, sub, sll, xor, srl, sra, or, and,
  lui, beq, bne, blt, bge, jalr, jal,
  plus slt/slti because they are already used in the repo tests.

Usage examples:
  python3 tools/riscv_asm_to_hex.py program.s
  python3 tools/riscv_asm_to_hex.py program.s -o riscvtest.txt
  python3 tools/riscv_asm_to_hex.py - <<'EOF'
  start:
    addi x1, x0, 96
    beq  x1, x0, done
    jal  x2, start
  done:
    sw   x1, 0(x0)
  EOF
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass


REGISTER_ALIASES = {
    "zero": 0,
    "ra": 1,
    "sp": 2,
    "gp": 3,
    "tp": 4,
    "t0": 5,
    "t1": 6,
    "t2": 7,
    "s0": 8,
    "fp": 8,
    "s1": 9,
    "a0": 10,
    "a1": 11,
    "a2": 12,
    "a3": 13,
    "a4": 14,
    "a5": 15,
    "a6": 16,
    "a7": 17,
    "s2": 18,
    "s3": 19,
    "s4": 20,
    "s5": 21,
    "s6": 22,
    "s7": 23,
    "s8": 24,
    "s9": 25,
    "s10": 26,
    "s11": 27,
    "t3": 28,
    "t4": 29,
    "t5": 30,
    "t6": 31,
}

R_TYPE = {
    "add": (0b000, 0b0000000),
    "sub": (0b000, 0b0100000),
    "sll": (0b001, 0b0000000),
    "slt": (0b010, 0b0000000),
    "xor": (0b100, 0b0000000),
    "srl": (0b101, 0b0000000),
    "sra": (0b101, 0b0100000),
    "or": (0b110, 0b0000000),
    "and": (0b111, 0b0000000),
}

I_TYPE_ALU = {
    "addi": 0b000,
    "slti": 0b010,
    "xori": 0b100,
    "ori": 0b110,
    "andi": 0b111,
}

SHIFT_IMM = {
    "slli": (0b001, 0b0000000),
    "srli": (0b101, 0b0000000),
    "srai": (0b101, 0b0100000),
}

BRANCHES = {
    "beq": 0b000,
    "bne": 0b001,
    "blt": 0b100,
    "bge": 0b101,
}


@dataclass
class SourceLine:
    pc: int
    text: str
    lineno: int


class AssemblerError(Exception):
    pass


def strip_comment(line: str) -> str:
    return re.split(r"[#;]", line, maxsplit=1)[0].strip()


def parse_register(token: str) -> int:
    token = token.strip().lower()
    if re.fullmatch(r"x([0-9]|[12][0-9]|3[01])", token):
        return int(token[1:])
    if token in REGISTER_ALIASES:
        return REGISTER_ALIASES[token]
    raise AssemblerError(f"Unknown register '{token}'")


def parse_int(token: str) -> int:
    token = token.strip().lower().replace("_", "")
    return int(token, 0)


def parse_imm_or_label(token: str, labels: dict[str, int], pc: int, relative: bool) -> int:
    token = token.strip()
    try:
        return parse_int(token)
    except ValueError:
        if token not in labels:
            raise AssemblerError(f"Unknown label '{token}'")
        target = labels[token]
        return target - pc if relative else target


def check_signed(value: int, bits: int, what: str) -> int:
    low = -(1 << (bits - 1))
    high = (1 << (bits - 1)) - 1
    if not (low <= value <= high):
        raise AssemblerError(f"{what} out of range for {bits} signed bits: {value}")
    return value & ((1 << bits) - 1)


def check_unsigned(value: int, bits: int, what: str) -> int:
    if not (0 <= value < (1 << bits)):
        raise AssemblerError(f"{what} out of range for {bits} unsigned bits: {value}")
    return value


def encode_r(rd: int, rs1: int, rs2: int, funct3: int, funct7: int) -> int:
    opcode = 0b0110011
    return (funct7 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode


def encode_i(rd: int, rs1: int, imm: int, funct3: int, opcode: int) -> int:
    imm12 = check_signed(imm, 12, "Immediate")
    return (imm12 << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode


def encode_shift_imm(rd: int, rs1: int, shamt: int, funct3: int, funct7: int) -> int:
    shamt = check_unsigned(shamt, 5, "Shift amount")
    opcode = 0b0010011
    return (funct7 << 25) | (shamt << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode


def encode_s(rs1: int, rs2: int, imm: int, funct3: int) -> int:
    opcode = 0b0100011
    imm12 = check_signed(imm, 12, "Store immediate")
    return (((imm12 >> 5) & 0x7F) << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | ((imm12 & 0x1F) << 7) | opcode


def encode_b(rs1: int, rs2: int, offset: int, funct3: int) -> int:
    opcode = 0b1100011
    if offset % 2 != 0:
        raise AssemblerError(f"Branch offset must be 2-byte aligned: {offset}")
    imm13 = check_signed(offset, 13, "Branch offset")
    bit12 = (imm13 >> 12) & 0x1
    bit11 = (imm13 >> 11) & 0x1
    bits10_5 = (imm13 >> 5) & 0x3F
    bits4_1 = (imm13 >> 1) & 0xF
    return (bit12 << 31) | (bits10_5 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (bits4_1 << 8) | (bit11 << 7) | opcode


def encode_u(rd: int, imm: int) -> int:
    opcode = 0b0110111
    imm20 = check_unsigned(imm, 20, "LUI immediate")
    return (imm20 << 12) | (rd << 7) | opcode


def encode_j(rd: int, offset: int) -> int:
    opcode = 0b1101111
    if offset % 2 != 0:
        raise AssemblerError(f"JAL offset must be 2-byte aligned: {offset}")
    imm21 = check_signed(offset, 21, "JAL offset")
    bit20 = (imm21 >> 20) & 0x1
    bits10_1 = (imm21 >> 1) & 0x3FF
    bit11 = (imm21 >> 11) & 0x1
    bits19_12 = (imm21 >> 12) & 0xFF
    return (bit20 << 31) | (bits19_12 << 12) | (bit11 << 20) | (bits10_1 << 21) | (rd << 7) | opcode


def parse_offset_base(token: str) -> tuple[int, int]:
    match = re.fullmatch(r"\s*([^()]+)\(([^()]+)\)\s*", token)
    if not match:
        raise AssemblerError(f"Expected offset(base) operand, got '{token}'")
    offset = parse_int(match.group(1))
    base = parse_register(match.group(2))
    return offset, base


def tokenize_operands(operand_text: str) -> list[str]:
    if not operand_text.strip():
        return []
    return [part.strip() for part in operand_text.split(",")]


def parse_lines(text: str) -> tuple[list[SourceLine], dict[str, int]]:
    lines: list[SourceLine] = []
    labels: dict[str, int] = {}
    pc = 0

    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = strip_comment(raw)
        if not line:
            continue

        while ":" in line:
            label, rest = line.split(":", 1)
            label = label.strip()
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", label):
                raise AssemblerError(f"Invalid label '{label}' on line {lineno}")
            if label in labels:
                raise AssemblerError(f"Duplicate label '{label}' on line {lineno}")
            labels[label] = pc
            line = rest.strip()
            if not line:
                break

        if not line:
            continue

        lines.append(SourceLine(pc=pc, text=line, lineno=lineno))
        pc += 4

    return lines, labels


def assemble_line(src: SourceLine, labels: dict[str, int]) -> int:
    parts = src.text.split(None, 1)
    mnemonic = parts[0].lower()
    operands = tokenize_operands(parts[1] if len(parts) > 1 else "")

    if mnemonic in R_TYPE:
        if len(operands) != 3:
            raise AssemblerError(f"Line {src.lineno}: {mnemonic} expects rd, rs1, rs2")
        rd = parse_register(operands[0])
        rs1 = parse_register(operands[1])
        rs2 = parse_register(operands[2])
        funct3, funct7 = R_TYPE[mnemonic]
        return encode_r(rd, rs1, rs2, funct3, funct7)

    if mnemonic in I_TYPE_ALU:
        if len(operands) != 3:
            raise AssemblerError(f"Line {src.lineno}: {mnemonic} expects rd, rs1, imm")
        rd = parse_register(operands[0])
        rs1 = parse_register(operands[1])
        imm = parse_int(operands[2])
        return encode_i(rd, rs1, imm, I_TYPE_ALU[mnemonic], 0b0010011)

    if mnemonic in SHIFT_IMM:
        if len(operands) != 3:
            raise AssemblerError(f"Line {src.lineno}: {mnemonic} expects rd, rs1, shamt")
        rd = parse_register(operands[0])
        rs1 = parse_register(operands[1])
        shamt = parse_int(operands[2])
        funct3, funct7 = SHIFT_IMM[mnemonic]
        return encode_shift_imm(rd, rs1, shamt, funct3, funct7)

    if mnemonic == "lw":
        if len(operands) != 2:
            raise AssemblerError(f"Line {src.lineno}: lw expects rd, imm(rs1)")
        rd = parse_register(operands[0])
        offset, rs1 = parse_offset_base(operands[1])
        return encode_i(rd, rs1, offset, 0b010, 0b0000011)

    if mnemonic == "jalr":
        if len(operands) != 2:
            raise AssemblerError(f"Line {src.lineno}: jalr expects rd, imm(rs1)")
        rd = parse_register(operands[0])
        offset, rs1 = parse_offset_base(operands[1])
        return encode_i(rd, rs1, offset, 0b000, 0b1100111)

    if mnemonic == "sw":
        if len(operands) != 2:
            raise AssemblerError(f"Line {src.lineno}: sw expects rs2, imm(rs1)")
        rs2 = parse_register(operands[0])
        offset, rs1 = parse_offset_base(operands[1])
        return encode_s(rs1, rs2, offset, 0b010)

    if mnemonic in BRANCHES:
        if len(operands) != 3:
            raise AssemblerError(f"Line {src.lineno}: {mnemonic} expects rs1, rs2, label/offset")
        rs1 = parse_register(operands[0])
        rs2 = parse_register(operands[1])
        offset = parse_imm_or_label(operands[2], labels, src.pc, relative=True)
        return encode_b(rs1, rs2, offset, BRANCHES[mnemonic])

    if mnemonic == "jal":
        if len(operands) != 2:
            raise AssemblerError(f"Line {src.lineno}: jal expects rd, label/offset")
        rd = parse_register(operands[0])
        offset = parse_imm_or_label(operands[1], labels, src.pc, relative=True)
        return encode_j(rd, offset)

    if mnemonic == "lui":
        if len(operands) != 2:
            raise AssemblerError(f"Line {src.lineno}: lui expects rd, imm20")
        rd = parse_register(operands[0])
        imm = parse_int(operands[1])
        return encode_u(rd, imm)

    if mnemonic == "nop":
        return 0x00000013  # addi x0, x0, 0

    raise AssemblerError(f"Line {src.lineno}: Unsupported instruction '{mnemonic}'")


def assemble_text(text: str) -> list[int]:
    lines, labels = parse_lines(text)
    return [assemble_line(src, labels) for src in lines]


def main() -> int:
    parser = argparse.ArgumentParser(description="Assemble a small RISC-V subset to hex words")
    parser.add_argument("input", help="Assembly file path, or '-' to read stdin")
    parser.add_argument("-o", "--output", help="Write hex words to this file instead of stdout")
    parser.add_argument("--pc-base", type=lambda x: int(x, 0), default=0, help="Accepted for future use; labels currently assume base 0")
    args = parser.parse_args()

    if args.pc_base != 0:
        raise AssemblerError("Only pc base 0 is supported for now")

    if args.input == "-":
        source = sys.stdin.read()
    else:
        with open(args.input, "r", encoding="utf-8") as f:
            source = f.read()

    try:
        words = assemble_text(source)
    except AssemblerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    output_text = "\n".join(f"{word:08X}" for word in words) + ("\n" if words else "")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_text)
    else:
        sys.stdout.write(output_text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
