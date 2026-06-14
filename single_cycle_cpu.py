from riscy.reference_cpu import (
    ABI_NAMES,
    ReferenceCPU,
    StepResult,
    disassemble_word,
    instruction_info,
)


class SingleCycleCPU(ReferenceCPU):

    model_name = "single-cycle"
