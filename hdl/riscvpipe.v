module riscvpipe(input  clk, reset,
                 output [31:0] PCF,
                 input  [31:0] InstrF,
                 output MemWriteM,
                 output [31:0] DataAdrM,
                 output [31:0] WriteDataM,
                 input  [31:0] ReadDataM);
  
  wire [6:0] opD;
  wire [2:0] funct3D;
  wire       funct7b5D;
  wire       ZeroE;
  wire       CondBitE;
  wire       PCSrcE, ALUSrcE, JalrE, RegWriteW;
  wire [1:0] ResultSrcW, ImmSrcD;
  wire [3:0] ALUControlE;

  controller c(
    .clk(clk),
    .reset(reset),
    .opD(opD),
    .funct3D(funct3D),
    .funct7b5D(funct7b5D),
    .ZeroE(ZeroE),
    .CondBitE(CondBitE),
    .ResultSrcW(ResultSrcW),
    .MemWriteM(MemWriteM),
    .PCSrcE(PCSrcE),
    .ALUSrcE(ALUSrcE),
    .JalrE(JalrE),
    .RegWriteW(RegWriteW),
    .ImmSrcD(ImmSrcD),
    .ALUControlE(ALUControlE)
  );

  datapath dp(
    .clk(clk),
    .reset(reset),
    .ResultSrcW(ResultSrcW),
    .PCSrcE(PCSrcE),
    .ALUSrcE(ALUSrcE),
    .JalrE(JalrE),
    .RegWriteW(RegWriteW),
    .ImmSrcD(ImmSrcD),
    .ALUControlE(ALUControlE),
    .ZeroE(ZeroE),
    .CondBitE(CondBitE),
    .opD(opD),
    .funct3D(funct3D),
    .funct7b5D(funct7b5D),
    .PCF(PCF),
    .InstrF(InstrF),
    .ALUResultM(DataAdrM),
    .WriteDataM(WriteDataM),
    .ReadDataM(ReadDataM)
  );
endmodule
