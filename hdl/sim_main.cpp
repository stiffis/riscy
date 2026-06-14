#include "Vtop.h"
#include "Vtop___024root.h"
#include "verilated.h"
#include <cstdint>

struct Sim {
    VerilatedContext* ctx;
    Vtop* top;
};

static void tick(Sim* s) {
    s->top->clk = 0;
    s->top->eval();
    s->top->clk = 1;
    s->top->eval();
}

extern "C" {

Sim* sim_new() {
    Sim* s = new Sim;
    s->ctx = new VerilatedContext;
    s->top = new Vtop(s->ctx);
    s->top->clk = 0;
    s->top->reset = 0;
    return s;
}

void sim_free(Sim* s) {
    delete s->top;
    delete s->ctx;
    delete s;
}

void sim_load(Sim* s, const uint32_t* words, int n) {
    s->top->eval();
    for (int i = 0; i < 64; i++)
        s->top->rootp->top__DOT__imem__DOT__RAM[i] = (i < n) ? words[i] : 0u;
}

void sim_pulse_reset(Sim* s) {
    s->top->reset = 1;
    tick(s);
    tick(s);
    s->top->reset = 0;
    s->top->clk = 0;
    s->top->eval();
}

void sim_step(Sim* s) {
    tick(s);
}

uint32_t sim_pc(Sim* s)                { return s->top->rootp->top__DOT__PCF; }
uint32_t sim_reg(Sim* s, int i)        { return s->top->rootp->top__DOT__rvpipe__DOT__dp__DOT__rf__DOT__rf[i]; }
uint32_t sim_dmem(Sim* s, int word)    { return s->top->rootp->top__DOT__dmem__DOT__RAM[word]; }
uint32_t sim_imem(Sim* s, int word)    { return s->top->rootp->top__DOT__imem__DOT__RAM[word]; }

uint32_t sim_instr_f(Sim* s)           { return s->top->rootp->top__DOT__InstrF; }
uint32_t sim_instr_d(Sim* s)           { return s->top->rootp->top__DOT__rvpipe__DOT__dp__DOT__InstrD; }
uint32_t sim_pc_d(Sim* s)              { return s->top->rootp->top__DOT__rvpipe__DOT__dp__DOT__PCD; }
uint32_t sim_pc_e(Sim* s)              { return s->top->rootp->top__DOT__rvpipe__DOT__dp__DOT__PCE; }
uint32_t sim_rd_e(Sim* s)              { return s->top->rootp->top__DOT__rvpipe__DOT__dp__DOT__RdE; }
uint32_t sim_rd_m(Sim* s)              { return s->top->rootp->top__DOT__rvpipe__DOT__dp__DOT__RdM; }
uint32_t sim_rd_w(Sim* s)              { return s->top->rootp->top__DOT__rvpipe__DOT__dp__DOT__RdW; }
uint32_t sim_memwrite_m(Sim* s)        { return s->top->rootp->top__DOT__MemWrite; }

}
