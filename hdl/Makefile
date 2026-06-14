VERILATOR ?= verilator
VINC := $(shell $(VERILATOR) --getenv VERILATOR_ROOT)/include
TARGET := libriscy_vtop.so

VSRCS := top.v riscvpipe.v controller.v datapath.v maindec.v aludec.v alu.v \
         extend.v flopr.v adder.v mux2.v mux3.v regfile.v imem.v dmem.v

$(TARGET): sim_main.cpp $(VSRCS)
	$(VERILATOR) --cc --public --build -Wno-fatal --top-module top -CFLAGS -fPIC $(VSRCS)
	g++ -O2 -fPIC -shared -I obj_dir -I $(VINC) -I $(VINC)/vltstd \
	    sim_main.cpp obj_dir/Vtop__ALL.a \
	    $(VINC)/verilated.cpp $(VINC)/verilated_threads.cpp \
	    -lpthread -o $(TARGET)

clean:
	rm -rf obj_dir $(TARGET)

.PHONY: clean
