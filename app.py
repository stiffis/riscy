from __future__ import annotations

import argparse
import curses
import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from riscy.asm_loader import load_program
from riscy.single_cycle_cpu import ABI_NAMES, SingleCycleCPU, disassemble_word, instruction_info
from riscy.verilog_backend import DEFAULT_LIB, VerilogPipelineCPU


PROGRAM_LINES = 14
MEMORY_LINES = 16
DEFAULT_ATTR = 0

CTRL_H = 8
CTRL_J = 10
CTRL_K = 11
CTRL_L = 12

PROGRAM = "program"
MEMORY = "memory"
REGISTERS = "registers"

FOCUS_MOVES = {
    (PROGRAM, CTRL_J): MEMORY,
    (PROGRAM, CTRL_L): REGISTERS,
    (MEMORY, CTRL_K): PROGRAM,
    (MEMORY, CTRL_L): REGISTERS,
    (REGISTERS, CTRL_H): PROGRAM,
}


@dataclass
class UIState:
    focus: str = PROGRAM
    mem_base: int = 0
    prog_top: int = 0
    prog_cursor: int = 0
    reg_top: int = 0
    help_visible: bool = False
    backend_visible: bool = False
    backend_index: int = 0


HELP_LINES = [
    "s             step one instruction",
    "n             run 10 instructions",
    "c             continue (until breakpoint or halt)",
    "g             run to end (safety-limited)",
    "t             run to cursor line",
    "b             toggle breakpoint at cursor",
    "r             reset CPU and memory",
    "Ctrl+h/j/k/l  move focus between windows",
    "j / k         scroll the focused window",
    "p             recenter focused window on PC",
    "m             select execution backend",
    "?             toggle this help",
    "q             quit",
]

STAGE_NAMES = ["IF", "ID", "EX", "MEM", "WB"]


def draw_box(
    win,
    y: int,
    x: int,
    h: int,
    w: int,
    title: str,
    title_attr: int | None = None,
    border_attr: int | None = None,
) -> None:
    max_y, max_x = win.getmaxyx()
    if h < 3 or w < 4 or y < 0 or x < 0 or y >= max_y or x >= max_x:
        return

    right = min(x + w - 1, max_x - 2)
    bottom = min(y + h - 1, max_y - 2)
    if right <= x or bottom <= y + 1:
        return

    border_attr = DEFAULT_ATTR if border_attr is None else border_attr
    title_attr = border_attr if title_attr is None else title_attr

    inner_w = right - x - 1
    title_text = f"─[{title}]"
    top_fill = max(0, inner_w - len(title_text))
    top_line = f"┌{title_text}{'─' * top_fill}┐"
    bottom_line = f"└{'─' * inner_w}┘"

    safe_addstr(win, y + 1, x, top_line, border_attr)
    for row in range(y + 2, bottom):
        safe_addstr(win, row, x, "│", border_attr)
        safe_addstr(win, row, right, "│", border_attr)
    safe_addstr(win, bottom, x, bottom_line, border_attr)
    safe_addstr(win, y + 1, x + 2, f"[{title}]", title_attr)


def safe_addstr(win, y: int, x: int, text: str, attr: int | None = None) -> None:
    max_y, max_x = win.getmaxyx()
    if y < 0 or y >= max_y or x >= max_x:
        return
    clipped = text[: max(0, max_x - x - 1)]
    if clipped:
        win.addstr(y, x, clipped, DEFAULT_ATTR if attr is None else attr)


def format_reg_line(idx: int, value: int) -> str:
    return f"x{idx:02d} {ABI_NAMES[idx]:>4}  0x{value:08X}"


def draw_pipeline(stdscr, cpu, pipe_y, width, normal_attr, pc_attr, ok_attr, dim_attr) -> None:
    stages = cpu.pipeline_stages()
    safe_addstr(stdscr, pipe_y + 1, 14, f" cycle {cpu.step_count} ", dim_attr)
    cell_w = max(10, (width - 4) // 5)
    name_row = pipe_y + 2
    instr_row = pipe_y + 3
    stage_attr = {0: pc_attr, 4: ok_attr}
    for i, (name, pc, instr) in enumerate(stages):
        x = 2 + i * cell_w
        attr = stage_attr.get(i, normal_attr)
        if i > 0:
            safe_addstr(stdscr, instr_row, x - 2, "▶", dim_attr)
        safe_addstr(stdscr, name_row, x, name, attr | curses.A_BOLD)
        if pc is None:
            safe_addstr(stdscr, instr_row, x, "· bubble", dim_attr)
        else:
            text = f"0x{pc:02X} {disassemble_word(instr, pc)}"
            safe_addstr(stdscr, instr_row, x, text[: cell_w - 2], attr)


def render(stdscr, cpu, program_name: str, ui: UIState, backends) -> None:
    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()
    if max_y < 28 or max_x < 110:
        safe_addstr(stdscr, 0, 0, "Terminal too small. Need at least 110x28.")
        stdscr.refresh()
        return

    normal_attr = curses.color_pair(1)
    title_attr = curses.color_pair(2) | curses.A_BOLD
    pc_attr = curses.color_pair(3) | curses.A_BOLD
    changed_attr = curses.color_pair(4) | curses.A_BOLD
    ok_attr = curses.color_pair(5)
    warn_attr = curses.color_pair(6) | curses.A_BOLD
    dim_attr = normal_attr | curses.A_DIM
    border_attr = normal_attr | curses.A_BOLD
    focus_border = pc_attr
    focus_title = title_attr | curses.A_REVERSE

    def box_attrs(window: str) -> tuple[int, int]:
        if ui.focus == window:
            return focus_title, focus_border
        return title_attr, border_attr

    is_pipeline = hasattr(cpu, "pipeline_stages")
    backend = getattr(cpu, "model_name", "single-cycle")
    safe_addstr(stdscr, 0, 0, " COMP-ARCH TUI Debugger ", title_attr)
    safe_addstr(stdscr, 0, 28, f"backend: {backend}", pc_attr)
    safe_addstr(stdscr, 1, 0, f"file: {program_name}", normal_attr)
    safe_addstr(stdscr, 1, max(46, len(program_name) + 12), "press ? for keybindings | m for backend", dim_attr)

    current_word = cpu.instruction_at(cpu.pc)
    halted_attr = warn_attr if cpu.halted else ok_attr
    state = "HALTED" if cpu.halted else "running"
    unit = "cycles" if is_pipeline else "steps"
    segments = [
        (f"PC 0x{cpu.pc:08X}", pc_attr),
        (f"{unit} {cpu.step_count}", normal_attr),
        (f"state {state}", halted_attr),
        (f"bkpts {len(cpu.breakpoints)}", normal_attr),
        (f"focus {ui.focus}", dim_attr),
    ]
    if cpu.halted and cpu.last_result.events:
        segments.append((f"reason: {cpu.last_result.events[-1]}", warn_attr))
    x = 0
    for i, (text, attr) in enumerate(segments):
        if i > 0:
            safe_addstr(stdscr, 2, x, " │ ", dim_attr)
            x += 3
        safe_addstr(stdscr, 2, x, text, attr)
        x += len(text)

    body_y = 4
    body_h = max_y - body_y - 1
    reg_w = 30
    left_w = max_x - reg_w
    pipe_h = 5 if is_pipeline else 0
    content_h = body_h - pipe_h
    program_h = min(18, content_h - 8)
    pipe_y = body_y + program_h
    bottom_y = pipe_y + pipe_h
    bottom_h = content_h - program_h
    info_w = max(32, min(40, left_w // 3))
    program_w = left_w
    program_list_w = min(left_w - info_w, 68)
    if program_list_w < 56:
        program_list_w = left_w - info_w

    prog_title, prog_border = box_attrs(PROGRAM)
    reg_title, reg_border = box_attrs(REGISTERS)
    mem_title, mem_border = box_attrs(MEMORY)
    draw_box(stdscr, body_y, 0, program_h, program_w, "Program", prog_title, prog_border)
    draw_box(stdscr, body_y, left_w, body_h, reg_w, "Registers", reg_title, reg_border)
    draw_box(stdscr, bottom_y, 0, bottom_h, left_w, "Memory", mem_title, mem_border)
    if is_pipeline:
        draw_box(stdscr, pipe_y, 0, pipe_h, left_w, "Pipeline", title_attr, border_attr)
        draw_pipeline(stdscr, cpu, pipe_y, left_w, normal_attr, pc_attr, ok_attr, dim_attr)

    sep_x = program_list_w
    prog_bottom = min(body_y + program_h - 1, max_y - 2)
    for row in range(body_y + 2, prog_bottom):
        safe_addstr(stdscr, row, sep_x, "│", border_attr)
    info_x = sep_x + 2
    safe_addstr(stdscr, body_y + 2, info_x, "Current Instr", title_attr)

    info_divider_y = body_y + 10
    info_right = min(program_w - 2, max_x - 3)
    if info_divider_y < prog_bottom:
        for col in range(sep_x + 1, info_right):
            safe_addstr(stdscr, info_divider_y, col, "─", border_attr)
        safe_addstr(stdscr, info_divider_y + 1, info_x, "Last Step", title_attr)

    if ui.prog_cursor < ui.prog_top:
        ui.prog_top = ui.prog_cursor
    elif ui.prog_cursor >= ui.prog_top + PROGRAM_LINES:
        ui.prog_top = ui.prog_cursor - PROGRAM_LINES + 1
    ui.prog_top = max(0, ui.prog_top)

    for row, index in enumerate(range(ui.prog_top, ui.prog_top + PROGRAM_LINES), start=6):
        addr = index * 4
        word = cpu.instruction_at(addr)
        bp_char = "●" if addr in cpu.breakpoints else " "
        pc_char = ">" if addr == cpu.pc else " "
        marker = f"{bp_char}{pc_char}"
        if addr == cpu.pc:
            attr = pc_attr
        elif addr in cpu.breakpoints:
            attr = warn_attr
        else:
            attr = normal_attr
        if index == ui.prog_cursor:
            attr = attr | curses.A_REVERSE
        asm_text = disassemble_word(word, addr)
        text = f"{marker} {index:03d}  0x{addr:08X}  {asm_text:<32}  {word:08X}"
        safe_addstr(stdscr, row, 2, text, attr)

    info_lines = instruction_info(current_word, cpu.pc)
    for i, line in enumerate(info_lines[: max(1, info_divider_y - (body_y + 3))]):
        safe_addstr(stdscr, 7 + i, info_x, line, normal_attr)

    event_rows_top = info_divider_y + 2
    event_rows = max(1, prog_bottom - event_rows_top)
    for i, event in enumerate(cpu.last_result.events[:event_rows]):
        attr = ok_attr if i == 0 else normal_attr
        safe_addstr(stdscr, event_rows_top + i, info_x, f"- {event}", attr)

    reg_y0 = body_y + 2
    reg_visible = max(1, min(32, body_h - 3))
    max_reg_top = max(0, 32 - reg_visible)
    ui.reg_top = max(0, min(ui.reg_top, max_reg_top))
    for row, idx in enumerate(range(ui.reg_top, min(32, ui.reg_top + reg_visible))):
        y = reg_y0 + row
        attr = changed_attr if idx in cpu.last_result.changed_registers else normal_attr
        safe_addstr(stdscr, y, left_w + 2, format_reg_line(idx, cpu.registers[idx]), attr)

    mem_header_y = bottom_y + 2
    safe_addstr(stdscr, mem_header_y, 2, f"base = 0x{ui.mem_base:08X}", dim_attr)
    safe_addstr(stdscr, mem_header_y, 24, f"PC word = 0x{cpu.pc:08X}", dim_attr)
    memory_rows = max(1, min(MEMORY_LINES, bottom_h - 4))
    for i in range(memory_rows):
        addr = ui.mem_base + i * 4
        value = cpu.data_word(addr)
        addr_attr = pc_attr if addr == cpu.pc else normal_attr
        value_attr = changed_attr if addr in cpu.last_result.changed_memory else normal_attr
        safe_addstr(stdscr, mem_header_y + 1 + i, 2, f"0x{addr:08X}", addr_attr)
        safe_addstr(stdscr, mem_header_y + 1 + i, 16, f"0x{value:08X}", value_attr)

    safe_addstr(stdscr, max_y - 1, 0, f" {backend} backend active ", title_attr)

    if ui.help_visible:
        hh = len(HELP_LINES) + 3
        hw = max(len(line) for line in HELP_LINES) + 6
        hy = max(0, (max_y - hh) // 2)
        hx = max(0, (max_x - hw) // 2)
        for r in range(1, hh):
            safe_addstr(stdscr, hy + r, hx, " " * hw, normal_attr)
        draw_box(stdscr, hy, hx, hh, hw, "Help", focus_title, focus_border)
        for i, line in enumerate(HELP_LINES):
            safe_addstr(stdscr, hy + 2 + i, hx + 2, line, normal_attr)

    if ui.backend_visible:
        lines = []
        for label, _factory, available in backends:
            suffix = "" if available else "  (unavailable: run make -C hdl)"
            lines.append(f"{label}{suffix}")
        hh = len(lines) + 4
        hw = max(len(line) for line in lines) + 8
        hy = max(0, (max_y - hh) // 2)
        hx = max(0, (max_x - hw) // 2)
        for r in range(1, hh):
            safe_addstr(stdscr, hy + r, hx, " " * hw, normal_attr)
        draw_box(stdscr, hy, hx, hh, hw, "Select backend", focus_title, focus_border)
        for i, line in enumerate(lines):
            available = backends[i][2]
            selected = i == ui.backend_index
            marker = "> " if selected else "  "
            base = normal_attr if available else dim_attr
            attr = (base | curses.A_REVERSE) if selected else base
            safe_addstr(stdscr, hy + 2 + i, hx + 2, f"{marker}{line}", attr)

    stdscr.refresh()


def scroll_focused(ui: UIState, cpu: SingleCycleCPU, delta: int) -> None:
    if ui.focus == PROGRAM:
        ui.prog_cursor = max(0, ui.prog_cursor + delta)
    elif ui.focus == MEMORY:
        if delta > 0:
            ui.mem_base = min(ui.mem_base + 16, 0xFFFFFFF0)
        else:
            ui.mem_base = max(ui.mem_base - 16, 0)
    elif ui.focus == REGISTERS:
        ui.reg_top = max(0, min(31, ui.reg_top + delta))


def recenter_focused(ui: UIState, cpu: SingleCycleCPU) -> None:
    if ui.focus == PROGRAM:
        ui.prog_cursor = cpu.pc // 4
    elif ui.focus == MEMORY:
        ui.mem_base = max(cpu.pc - 16, 0)
    elif ui.focus == REGISTERS:
        ui.reg_top = 0


def run_curses(stdscr, backends, program_name: str) -> None:
    global DEFAULT_ATTR
    curses.curs_set(0)
    stdscr.nodelay(False)
    stdscr.keypad(True)
    curses.start_color()
    curses.use_default_colors()
    white_color = 15 if curses.COLORS >= 16 else curses.COLOR_WHITE
    curses.init_pair(1, white_color, -1)
    curses.init_pair(2, curses.COLOR_MAGENTA, -1)
    curses.init_pair(3, curses.COLOR_CYAN, -1)
    curses.init_pair(4, curses.COLOR_YELLOW, -1)
    curses.init_pair(5, curses.COLOR_GREEN, -1)
    curses.init_pair(6, curses.COLOR_RED, -1)
    DEFAULT_ATTR = curses.color_pair(1)
    stdscr.bkgd(" ", DEFAULT_ATTR)

    cpu = backends[0][1]()
    ui = UIState(prog_cursor=cpu.pc // 4)
    while True:
        render(stdscr, cpu, program_name, ui, backends)
        key = stdscr.getch()
        if key in (ord("q"), ord("Q")):
            break
        if key == ord("?"):
            ui.help_visible = not ui.help_visible
            continue
        if ui.help_visible:
            ui.help_visible = False
            continue
        if ui.backend_visible:
            if key in (ord("j"), curses.KEY_DOWN):
                ui.backend_index = min(len(backends) - 1, ui.backend_index + 1)
            elif key in (ord("k"), curses.KEY_UP):
                ui.backend_index = max(0, ui.backend_index - 1)
            elif key in (curses.KEY_ENTER, 10, 13):
                if backends[ui.backend_index][2]:
                    cpu = backends[ui.backend_index][1]()
                    ui.prog_cursor = cpu.pc // 4
                    ui.prog_top = 0
                    ui.mem_base = 0
                ui.backend_visible = False
            else:
                ui.backend_visible = False
            continue
        if key in (ord("m"), ord("M")):
            ui.backend_visible = True
            continue
        if (ui.focus, key) in FOCUS_MOVES:
            ui.focus = FOCUS_MOVES[(ui.focus, key)]
        elif key in (ord("s"), ord("S")):
            cpu.step()
        elif key in (ord("n"), ord("N")):
            cpu.run(10)
        elif key in (ord("c"), ord("C")):
            cpu.continue_run()
        elif key in (ord("g"), ord("G")):
            cpu.run_to_end()
        elif key in (ord("t"), ord("T")):
            cpu.run_to_address(ui.prog_cursor * 4)
        elif key in (ord("b"), ord("B")):
            cpu.toggle_breakpoint(ui.prog_cursor * 4)
        elif key in (ord("r"), ord("R")):
            cpu.reset()
        elif key == ord("j"):
            scroll_focused(ui, cpu, +1)
        elif key == ord("k"):
            scroll_focused(ui, cpu, -1)
        elif key in (ord("p"), ord("P")):
            recenter_focused(ui, cpu)


def main() -> int:
    parser = argparse.ArgumentParser(description="Simple TUI debugger for the COMP-ARCH RISC-V project")
    parser.add_argument("program", help="Input .s/.asm/.txt/.hex program")
    args = parser.parse_args()

    image = load_program(args.program)
    words = image.words
    backends = [
        ("single-cycle", lambda: SingleCycleCPU(words), True),
        ("pipeline (verilog)", lambda: VerilogPipelineCPU(words), DEFAULT_LIB.exists()),
    ]
    curses.wrapper(run_curses, backends, image.path.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
