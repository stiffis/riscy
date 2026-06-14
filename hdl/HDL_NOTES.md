# HDL vendoring notes

This directory contains a **verbatim copy** of the RISC-V pipeline HDL from the
author's university project at `class-notes/COMP-ARCH/week13/Src files/Src files`,
vendored into `riscy` on 2026-06-14 so the TUI can drive it through a Verilator
backend.

## Ground rule

The Verilog RTL is the university project and is **never modified**. Every `.v`
file here is byte-for-byte identical to the source (verified with `diff`). riscy
does not edit the original `week13` tree either.

To expose internal signals (register file, `PCF`, pipeline registers) to the C++
harness, the Verilator build uses the global **`--public`** flag — this requires
**no `verilator public` markers in the RTL**, so the source stays untouched.

## Files

### Vendored verbatim (do not edit)

- All `*.v` modules: `top.v`, `riscvpipe.v`, `controller.v`, `datapath.v`,
  `maindec.v`, `aludec.v`, `alu.v`, `extend.v`, `flopr.v`, `adder.v`, `mux2.v`,
  `mux3.v`, `regfile.v`, `imem.v`, `dmem.v`.
- The original Icarus testbenches `testbench*.v` (kept for reference; not used by
  the Verilator build).
- The program images `riscvtest*.txt`.

### Added by riscy (these are ours)

- `sim_main.cpp` — C++ harness exposing a small `extern "C"` API (reset, step,
  read PC / register / memory) over the Verilated model.
- `Makefile` — runs Verilator and builds the shared library used by the Python
  `VerilatorBackend`.

## Program loading

`imem.v` loads its instruction memory with `$readmemh("riscvtest.txt", RAM)`.
The harness writes the program words directly into the imem array after model
construction, so arbitrary programs can be loaded without depending on that file
and without editing `imem.v`.

## Updating the snapshot

If the university model changes, re-copy the `*.v` files from `week13` and
re-run `diff` to confirm they are verbatim. Do not hand-edit them here.
