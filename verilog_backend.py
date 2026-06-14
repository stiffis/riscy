from __future__ import annotations

import contextlib
import ctypes
import os
from pathlib import Path

from riscy.backend import CPUBackend, StepResult
from riscy.reference_cpu import disassemble_word, reg_name

DEFAULT_LIB = Path(__file__).resolve().parent / "hdl" / "libriscy_vtop.so"
DMEM_WORDS = 64


@contextlib.contextmanager
def _suppress_fd(fd: int = 2):
    saved = os.dup(fd)
    devnull = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull, fd)
        yield
    finally:
        os.dup2(saved, fd)
        os.close(devnull)
        os.close(saved)


class VerilogPipelineCPU(CPUBackend):
    model_name = "pipeline (verilog)"

    def __init__(self, words: list[int], lib_path: Path | None = None):
        super().__init__()
        path = Path(lib_path) if lib_path else DEFAULT_LIB
        if not path.exists():
            raise FileNotFoundError(
                f"Verilator library not found at {path}. Build it with: make -C hdl"
            )
        self.words = words[:]
        self.program_end = len(words) * 4
        self._lib = ctypes.CDLL(str(path))
        self._bind()
        self._handle = None
        self.reset()

    def _bind(self) -> None:
        lib = self._lib
        lib.sim_new.restype = ctypes.c_void_p
        lib.sim_free.argtypes = [ctypes.c_void_p]
        lib.sim_load.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32), ctypes.c_int]
        lib.sim_pulse_reset.argtypes = [ctypes.c_void_p]
        lib.sim_step.argtypes = [ctypes.c_void_p]
        for name in ("sim_pc", "sim_instr_f", "sim_instr_d", "sim_pc_d", "sim_pc_e"):
            fn = getattr(lib, name)
            fn.argtypes = [ctypes.c_void_p]
            fn.restype = ctypes.c_uint32
        for name in ("sim_reg", "sim_dmem", "sim_imem"):
            fn = getattr(lib, name)
            fn.argtypes = [ctypes.c_void_p, ctypes.c_int]
            fn.restype = ctypes.c_uint32

    def _read_registers(self) -> list[int]:
        return [self._lib.sim_reg(self._handle, i) for i in range(32)]

    def _read_dmem(self) -> dict[int, int]:
        out = {}
        for i in range(DMEM_WORDS):
            value = self._lib.sim_dmem(self._handle, i)
            if value:
                out[i * 4] = value
        return out

    def reset(self) -> None:
        if self._handle is not None:
            self._lib.sim_free(self._handle)
        arr = (ctypes.c_uint32 * len(self.words))(*self.words)
        with _suppress_fd(1), _suppress_fd(2):
            self._handle = ctypes.c_void_p(self._lib.sim_new())
            self._lib.sim_load(self._handle, arr, len(self.words))
            self._lib.sim_pulse_reset(self._handle)
        self.pc = self._lib.sim_pc(self._handle)
        self.registers = self._read_registers()
        self.memory = self._read_dmem()
        self.step_count = 0
        self.halted = False
        self._idle = 0
        self.last_result = StepResult(self.pc, self._lib.sim_imem(self._handle, self.pc >> 2), "reset", [], [], ["pipeline reset"])

    def step(self) -> StepResult:
        if self.halted:
            return self.last_result

        pc_before = self.pc
        instr = self._lib.sim_imem(self._handle, pc_before >> 2)
        regs_before = self.registers
        mem_before = self.memory

        self._lib.sim_step(self._handle)

        regs_after = self._read_registers()
        mem_after = self._read_dmem()
        self.pc = self._lib.sim_pc(self._handle)
        self.step_count += 1

        changed_registers = [i for i in range(32) if regs_after[i] != regs_before[i]]
        changed_memory = [addr for addr in set(mem_before) | set(mem_after) if mem_before.get(addr, 0) != mem_after.get(addr, 0)]

        events = [f"cycle {self.step_count}"]
        for i in changed_registers:
            events.append(f"{reg_name(i)} <- 0x{regs_after[i]:08X}")
        for addr in sorted(changed_memory):
            events.append(f"store 0x{mem_after.get(addr, 0):08X} -> [0x{addr:08X}]")

        self.registers = regs_after
        self.memory = mem_after
        if self.pc >= self.program_end and not changed_registers and not changed_memory:
            self._idle += 1
        else:
            self._idle = 0
        if self._idle >= 5:
            self.halted = True
            events.append("program drained")

        self.last_result = StepResult(
            pc_before=pc_before,
            instruction=instr,
            disasm=disassemble_word(instr, pc_before),
            changed_registers=changed_registers,
            changed_memory=changed_memory,
            events=events,
        )
        return self.last_result
