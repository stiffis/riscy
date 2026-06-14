from __future__ import annotations

from riscy.backend import CPUBackend, StepResult


ABI_NAMES = [
    "zero", "ra", "sp", "gp", "tp", "t0", "t1", "t2",
    "s0", "s1", "a0", "a1", "a2", "a3", "a4", "a5",
    "a6", "a7", "s2", "s3", "s4", "s5", "s6", "s7",
    "s8", "s9", "s10", "s11", "t3", "t4", "t5", "t6",
]


def sign_extend(value: int, bits: int) -> int:
    sign_bit = 1 << (bits - 1)
    mask = (1 << bits) - 1
    value &= mask
    return (value ^ sign_bit) - sign_bit


def to_signed32(value: int) -> int:
    return sign_extend(value, 32)


def decode_i_imm(word: int) -> int:
    return sign_extend(word >> 20, 12)


def decode_s_imm(word: int) -> int:
    imm = ((word >> 25) << 5) | ((word >> 7) & 0x1F)
    return sign_extend(imm, 12)


def decode_b_imm(word: int) -> int:
    imm = (
        (((word >> 31) & 0x1) << 12)
        | (((word >> 7) & 0x1) << 11)
        | (((word >> 25) & 0x3F) << 5)
        | (((word >> 8) & 0xF) << 1)
    )
    return sign_extend(imm, 13)


def decode_j_imm(word: int) -> int:
    imm = (
        (((word >> 31) & 0x1) << 20)
        | (((word >> 12) & 0xFF) << 12)
        | (((word >> 20) & 0x1) << 11)
        | (((word >> 21) & 0x3FF) << 1)
    )
    return sign_extend(imm, 21)


def decode_u_imm(word: int) -> int:
    return word & 0xFFFFF000


def reg_name(idx: int) -> str:
    return f"x{idx}({ABI_NAMES[idx]})"


def disassemble_word(word: int, pc: int = 0) -> str:
    opcode = word & 0x7F
    rd = (word >> 7) & 0x1F
    funct3 = (word >> 12) & 0x7
    rs1 = (word >> 15) & 0x1F
    rs2 = (word >> 20) & 0x1F
    funct7 = (word >> 25) & 0x7F

    if word == 0x00000013:
        return "nop"

    if opcode == 0x33:
        table = {
            (0x0, 0x00): "add",
            (0x0, 0x20): "sub",
            (0x1, 0x00): "sll",
            (0x2, 0x00): "slt",
            (0x4, 0x00): "xor",
            (0x5, 0x00): "srl",
            (0x5, 0x20): "sra",
            (0x6, 0x00): "or",
            (0x7, 0x00): "and",
        }
        name = table.get((funct3, funct7), "unknown-r")
        return f"{name} x{rd}, x{rs1}, x{rs2}"

    if opcode == 0x13:
        imm = decode_i_imm(word)
        if funct3 == 0x0:
            return f"addi x{rd}, x{rs1}, {imm}"
        if funct3 == 0x2:
            return f"slti x{rd}, x{rs1}, {imm}"
        if funct3 == 0x4:
            return f"xori x{rd}, x{rs1}, {imm}"
        if funct3 == 0x6:
            return f"ori x{rd}, x{rs1}, {imm}"
        if funct3 == 0x7:
            return f"andi x{rd}, x{rs1}, {imm}"
        shamt = (word >> 20) & 0x1F
        if funct3 == 0x1 and funct7 == 0x00:
            return f"slli x{rd}, x{rs1}, {shamt}"
        if funct3 == 0x5 and funct7 == 0x00:
            return f"srli x{rd}, x{rs1}, {shamt}"
        if funct3 == 0x5 and funct7 == 0x20:
            return f"srai x{rd}, x{rs1}, {shamt}"
        return f"unknown-i 0x{word:08X}"

    if opcode == 0x03 and funct3 == 0x2:
        return f"lw x{rd}, {decode_i_imm(word)}(x{rs1})"

    if opcode == 0x23 and funct3 == 0x2:
        return f"sw x{rs2}, {decode_s_imm(word)}(x{rs1})"

    if opcode == 0x63:
        names = {0x0: "beq", 0x1: "bne", 0x4: "blt", 0x5: "bge"}
        name = names.get(funct3, "unknown-b")
        target = pc + decode_b_imm(word)
        return f"{name} x{rs1}, x{rs2}, 0x{target:08X}"

    if opcode == 0x37:
        return f"lui x{rd}, 0x{decode_u_imm(word) >> 12:X}"

    if opcode == 0x6F:
        target = pc + decode_j_imm(word)
        return f"jal x{rd}, 0x{target:08X}"

    if opcode == 0x67 and funct3 == 0x0:
        return f"jalr x{rd}, {decode_i_imm(word)}(x{rs1})"

    return f"unknown 0x{word:08X}"


def instruction_info(word: int, pc: int = 0) -> list[str]:
    opcode = word & 0x7F
    rd = (word >> 7) & 0x1F
    funct3 = (word >> 12) & 0x7
    rs1 = (word >> 15) & 0x1F
    rs2 = (word >> 20) & 0x1F
    funct7 = (word >> 25) & 0x7F

    lines = [
        f"opcode : {opcode:07b}",
    ]

    if word == 0x00000013:
        lines.append("kind   : nop")
        return lines

    lines.extend(
        [
            f"rd     : {rd:05b} (x{rd})",
            f"rs1    : {rs1:05b} (x{rs1})",
            f"rs2    : {rs2:05b} (x{rs2})",
            f"funct3 : {funct3:03b}",
            f"funct7 : {funct7:07b}",
        ]
    )

    if opcode in {0x13, 0x03, 0x67}:
        lines.append(f"imm_i  : {(word >> 20) & 0xFFF:012b}")
    elif opcode == 0x23:
        imm_s = (((word >> 25) & 0x7F) << 5) | ((word >> 7) & 0x1F)
        lines.append(f"imm_s  : {imm_s:012b}")
    elif opcode == 0x63:
        offset = decode_b_imm(word)
        imm_b = (
            (((word >> 31) & 0x1) << 12)
            | (((word >> 7) & 0x1) << 11)
            | (((word >> 25) & 0x3F) << 5)
            | (((word >> 8) & 0xF) << 1)
        )
        lines.append(f"imm_b  : {imm_b:013b}")
        lines.append(f"target : 0x{(pc + offset) & 0xFFFFFFFF:08X}")
    elif opcode == 0x37:
        lines.append(f"imm_u  : {(decode_u_imm(word) >> 12):020b}")
    elif opcode == 0x6F:
        offset = decode_j_imm(word)
        imm_j = (
            (((word >> 31) & 0x1) << 20)
            | (((word >> 12) & 0xFF) << 12)
            | (((word >> 20) & 0x1) << 11)
            | (((word >> 21) & 0x3FF) << 1)
        )
        lines.append(f"imm_j  : {imm_j:021b}")
        lines.append(f"target : 0x{(pc + offset) & 0xFFFFFFFF:08X}")

    return lines


class ReferenceCPU(CPUBackend):
    model_name = "reference"

    def __init__(self, words: list[int], pc_base: int = 0):
        super().__init__()
        self.words = words[:]
        self.pc_base = pc_base
        self.initial_memory = {pc_base + index * 4: word for index, word in enumerate(words)}
        self.program_end = pc_base + len(words) * 4
        self.reset()

    def reset(self) -> None:
        self.registers = [0] * 32
        self.memory = dict(self.initial_memory)
        self.pc = self.pc_base
        self.step_count = 0
        self.halted = False
        self.last_result = StepResult(self.pc, self.memory.get(self.pc, 0), "reset", [], [], ["CPU reset"])

    def read_word(self, addr: int) -> int:
        if addr % 4 != 0:
            raise RuntimeError(f"Unaligned word access at 0x{addr:08X}")
        return self.memory.get(addr, 0)

    def write_word(self, addr: int, value: int) -> None:
        if addr % 4 != 0:
            raise RuntimeError(f"Unaligned word access at 0x{addr:08X}")
        self.memory[addr] = value & 0xFFFFFFFF

    def _write_reg(self, idx: int, value: int, changed: list[int], events: list[str]) -> None:
        if idx == 0:
            return
        self.registers[idx] = value & 0xFFFFFFFF
        changed.append(idx)
        events.append(f"{reg_name(idx)} <- 0x{self.registers[idx]:08X}")

    def step(self) -> StepResult:
        if self.halted:
            return self.last_result

        pc_before = self.pc
        word = self.read_word(pc_before)
        opcode = word & 0x7F
        rd = (word >> 7) & 0x1F
        funct3 = (word >> 12) & 0x7
        rs1 = (word >> 15) & 0x1F
        rs2 = (word >> 20) & 0x1F
        funct7 = (word >> 25) & 0x7F
        next_pc = (pc_before + 4) & 0xFFFFFFFF

        changed_registers: list[int] = []
        changed_memory: list[int] = []
        events = [f"PC=0x{pc_before:08X}"]
        disasm = disassemble_word(word, pc_before)

        r1 = self.registers[rs1]
        r2 = self.registers[rs2]

        if word == 0x00000013:
            events.append("nop")
        elif opcode == 0x33:
            if funct3 == 0x0 and funct7 == 0x00:
                self._write_reg(rd, r1 + r2, changed_registers, events)
            elif funct3 == 0x0 and funct7 == 0x20:
                self._write_reg(rd, r1 - r2, changed_registers, events)
            elif funct3 == 0x1 and funct7 == 0x00:
                self._write_reg(rd, r1 << (r2 & 0x1F), changed_registers, events)
            elif funct3 == 0x2 and funct7 == 0x00:
                self._write_reg(rd, int(to_signed32(r1) < to_signed32(r2)), changed_registers, events)
            elif funct3 == 0x4 and funct7 == 0x00:
                self._write_reg(rd, r1 ^ r2, changed_registers, events)
            elif funct3 == 0x5 and funct7 == 0x00:
                self._write_reg(rd, r1 >> (r2 & 0x1F), changed_registers, events)
            elif funct3 == 0x5 and funct7 == 0x20:
                self._write_reg(rd, to_signed32(r1) >> (r2 & 0x1F), changed_registers, events)
            elif funct3 == 0x6 and funct7 == 0x00:
                self._write_reg(rd, r1 | r2, changed_registers, events)
            elif funct3 == 0x7 and funct7 == 0x00:
                self._write_reg(rd, r1 & r2, changed_registers, events)
            else:
                self.halted = True
                events.append("Unsupported R-type instruction")
        elif opcode == 0x13:
            imm = decode_i_imm(word)
            if funct3 == 0x0:
                self._write_reg(rd, r1 + imm, changed_registers, events)
            elif funct3 == 0x2:
                self._write_reg(rd, int(to_signed32(r1) < imm), changed_registers, events)
            elif funct3 == 0x4:
                self._write_reg(rd, r1 ^ imm, changed_registers, events)
            elif funct3 == 0x6:
                self._write_reg(rd, r1 | imm, changed_registers, events)
            elif funct3 == 0x7:
                self._write_reg(rd, r1 & imm, changed_registers, events)
            elif funct3 == 0x1 and funct7 == 0x00:
                shamt = (word >> 20) & 0x1F
                self._write_reg(rd, r1 << shamt, changed_registers, events)
            elif funct3 == 0x5 and funct7 == 0x00:
                shamt = (word >> 20) & 0x1F
                self._write_reg(rd, r1 >> shamt, changed_registers, events)
            elif funct3 == 0x5 and funct7 == 0x20:
                shamt = (word >> 20) & 0x1F
                self._write_reg(rd, to_signed32(r1) >> shamt, changed_registers, events)
            else:
                self.halted = True
                events.append("Unsupported I-type ALU instruction")
        elif opcode == 0x03 and funct3 == 0x2:
            addr = (r1 + decode_i_imm(word)) & 0xFFFFFFFF
            value = self.read_word(addr)
            self._write_reg(rd, value, changed_registers, events)
            events.append(f"load from 0x{addr:08X}")
        elif opcode == 0x23 and funct3 == 0x2:
            addr = (r1 + decode_s_imm(word)) & 0xFFFFFFFF
            self.write_word(addr, r2)
            changed_memory.append(addr)
            events.append(f"store 0x{r2 & 0xFFFFFFFF:08X} -> [0x{addr:08X}]")
        elif opcode == 0x63:
            offset = decode_b_imm(word)
            taken = False
            if funct3 == 0x0:
                taken = r1 == r2
            elif funct3 == 0x1:
                taken = r1 != r2
            elif funct3 == 0x4:
                taken = to_signed32(r1) < to_signed32(r2)
            elif funct3 == 0x5:
                taken = to_signed32(r1) >= to_signed32(r2)
            else:
                self.halted = True
                events.append("Unsupported branch instruction")
            if not self.halted and taken:
                next_pc = (pc_before + offset) & 0xFFFFFFFF
                events.append(f"branch taken -> 0x{next_pc:08X}")
            elif not self.halted:
                events.append("branch not taken")
        elif opcode == 0x37:
            self._write_reg(rd, decode_u_imm(word), changed_registers, events)
        elif opcode == 0x6F:
            self._write_reg(rd, next_pc, changed_registers, events)
            next_pc = (pc_before + decode_j_imm(word)) & 0xFFFFFFFF
            events.append(f"jump -> 0x{next_pc:08X}")
        elif opcode == 0x67 and funct3 == 0x0:
            self._write_reg(rd, next_pc, changed_registers, events)
            next_pc = ((r1 + decode_i_imm(word)) & 0xFFFFFFFE) & 0xFFFFFFFF
            events.append(f"jump -> 0x{next_pc:08X}")
        elif word == 0x00000000 and pc_before >= self.program_end:
            self.halted = True
            events.append("end of program")
        else:
            self.halted = True
            events.append(f"Illegal instruction 0x{word:08X}")

        self.registers[0] = 0
        self.pc = next_pc
        self.step_count += 1
        self.last_result = StepResult(
            pc_before=pc_before,
            instruction=word,
            disasm=disasm,
            changed_registers=changed_registers,
            changed_memory=changed_memory,
            events=events,
        )
        return self.last_result
