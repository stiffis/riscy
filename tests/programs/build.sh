#!/bin/sh
# Assemble the RV32I test programs into flat raw binaries loadable at 0x0.
# Requires a RISC-V toolchain (riscv64-linux-gnu-{as,ld,objcopy}).
set -e
cd "$(dirname "$0")"

AS=riscv64-linux-gnu-as
LD=riscv64-linux-gnu-ld
OC=riscv64-linux-gnu-objcopy

for p in riscvtest tree quicksort; do
    "$AS" -march=rv32i -mabi=ilp32 -o "$p.o" "$p.s"
    "$LD" -m elf32lriscv -Ttext=0x0 -e _start -o "$p.elf" "$p.o" 2>/dev/null || \
    "$LD" -m elf32lriscv -Ttext=0x0 -o "$p.elf" "$p.o"
    "$OC" -O binary "$p.elf" "$p.bin"
    rm -f "$p.o" "$p.elf"
    echo "built $p.bin ($(wc -c < "$p.bin") bytes)"
done
