from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
ASSEMBLER_PATH = ROOT_DIR / "tools" / "riscv_asm_to_hex.py"


@dataclass
class ProgramImage:
    path: Path
    words: list[int]
    source_lines: list[str]


def _load_assembler_module():
    spec = importlib.util.spec_from_file_location("riscv_asm_to_hex", ASSEMBLER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load assembler module from {ASSEMBLER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_program(path_str: str) -> ProgramImage:
    path = Path(path_str).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(path)

    suffix = path.suffix.lower()

    if suffix == ".bin":
        data = path.read_bytes()
        words = [
            int.from_bytes(data[i:i + 4].ljust(4, b"\x00"), "little")
            for i in range(0, len(data), 4)
        ]
        return ProgramImage(path=path, words=words, source_lines=[f"{word:08X}" for word in words])

    text = path.read_text(encoding="utf-8")

    if suffix in {".s", ".asm"}:
        assembler = _load_assembler_module()
        words = assembler.assemble_text(text)
        source_lines = [line.rstrip() for line in text.splitlines()]
        return ProgramImage(path=path, words=words, source_lines=source_lines)

    if suffix in {".txt", ".hex"}:
        words: list[int] = []
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            words.append(int(line, 16))
        return ProgramImage(path=path, words=words, source_lines=[f"{word:08X}" for word in words])

    raise ValueError(f"Unsupported input type '{suffix}'. Use .s, .asm, .txt, .hex, or .bin")
