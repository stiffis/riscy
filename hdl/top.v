module top(input  clk, reset,
           output [31:0] WriteData, DataAdr,
           output MemWrite);
  
  wire [31:0] PCF, InstrF, ReadData;
  
  riscvpipe rvpipe(
    .clk(clk),
    .reset(reset),
    .PCF(PCF),
    .InstrF(InstrF),
    .MemWriteM(MemWrite),
    .DataAdrM(DataAdr),
    .WriteDataM(WriteData),
    .ReadDataM(ReadData)
  );

  imem imem(
    .a(PCF),
    .rd(InstrF)
  );

  dmem dmem(
    .clk(clk),
    .we(MemWrite),
    .a(DataAdr),
    .wd(WriteData),
    .rd(ReadData)
  );
endmodule
