module datapath(input  clk, reset,
                input  [1:0] ResultSrcW,
                input  PCSrcE, ALUSrcE, JalrE,
                input  RegWriteW,
                input  [1:0] ImmSrcD,
                input  [3:0] ALUControlE,
                output ZeroE,
                output CondBitE,
                output [6:0] opD,
                output [2:0] funct3D,
                output funct7b5D,
                output [31:0] PCF,
                input  [31:0] InstrF,
                output [31:0] ALUResultM, WriteDataM,
                input  [31:0] ReadDataM);
  
  localparam WIDTH = 32;

  wire [31:0] PCNextF, PCPlus4F;
  wire [31:0] InstrD, PCD, PCPlus4D;
  wire [31:0] RD1D, RD2D, ImmExtD;
  wire [31:0] RD1E, RD2E, PCE, ImmExtE, PCPlus4E;
  wire [31:0] SrcBE, ALUResultE, PCTargetE, PCBranchTargetE, PCJalrTargetE;
  wire [31:0] ALUResultW, ReadDataW, PCPlus4M, PCPlus4W;
  wire [31:0] ResultW;
  wire [4:0]  RdD, RdE, RdM, RdW;

  // Fetch stage
  flopr #(WIDTH) pcreg(
    .clk(clk),
    .reset(reset),
    .d(PCNextF),
    .q(PCF)
  );

  adder pcadd4(
    .a(PCF),
    .b(32'd4),
    .y(PCPlus4F)
  );

  mux2 #(WIDTH) pcmux(
    .d0(PCPlus4F),
    .d1(PCTargetE),
    .s(PCSrcE),
    .y(PCNextF)
  );

  // IF/ID pipeline register
  flopr #(WIDTH) ifid_instrreg(
    .clk(clk),
    .reset(reset),
    .d(InstrF),
    .q(InstrD)
  );

  flopr #(WIDTH) ifid_pcreg(
    .clk(clk),
    .reset(reset),
    .d(PCF),
    .q(PCD)
  );

  flopr #(WIDTH) ifid_pcplus4reg(
    .clk(clk),
    .reset(reset),
    .d(PCPlus4F),
    .q(PCPlus4D)
  );

  // Decode stage
  assign opD = InstrD[6:0];
  assign funct3D = InstrD[14:12];
  assign funct7b5D = InstrD[30];
  assign RdD = InstrD[11:7];

  regfile rf(
    .clk(clk),
    .we3(RegWriteW),
    .a1(InstrD[19:15]),
    .a2(InstrD[24:20]),
    .a3(RdW),
    .wd3(ResultW),
    .rd1(RD1D),
    .rd2(RD2D)
  );

  extend ext(
    .instr(InstrD[31:7]),
    .immsrc(ImmSrcD),
    .op(InstrD[6:0]),
    .immext(ImmExtD)
  );

  // ID/EX pipeline register
  flopr #(WIDTH) idex_rd1reg(
    .clk(clk),
    .reset(reset),
    .d(RD1D),
    .q(RD1E)
  );

  flopr #(WIDTH) idex_rd2reg(
    .clk(clk),
    .reset(reset),
    .d(RD2D),
    .q(RD2E)
  );

  flopr #(WIDTH) idex_pcreg(
    .clk(clk),
    .reset(reset),
    .d(PCD),
    .q(PCE)
  );

  flopr #(WIDTH) idex_immreg(
    .clk(clk),
    .reset(reset),
    .d(ImmExtD),
    .q(ImmExtE)
  );

  flopr #(5) idex_rdreg(
    .clk(clk),
    .reset(reset),
    .d(RdD),
    .q(RdE)
  );

  flopr #(WIDTH) idex_pcplus4reg(
    .clk(clk),
    .reset(reset),
    .d(PCPlus4D),
    .q(PCPlus4E)
  );

  // Execute stage
  mux2 #(WIDTH) srcbmux(
    .d0(RD2E),
    .d1(ImmExtE),
    .s(ALUSrcE),
    .y(SrcBE)
  );

  alu alu(
    .a(RD1E),
    .b(SrcBE),
    .alucontrol(ALUControlE),
    .result(ALUResultE),
    .zero(ZeroE)
  );

  adder pcaddbranch(
    .a(PCE),
    .b(ImmExtE),
    .y(PCBranchTargetE)
  );

  assign CondBitE = ALUResultE[0];
  assign PCJalrTargetE = {ALUResultE[31:1], 1'b0};
  assign PCTargetE = JalrE ? PCJalrTargetE : PCBranchTargetE;

  // EX/MEM pipeline register
  flopr #(WIDTH) exmem_aluresultreg(
    .clk(clk),
    .reset(reset),
    .d(ALUResultE),
    .q(ALUResultM)
  );

  flopr #(WIDTH) exmem_writedatareg(
    .clk(clk),
    .reset(reset),
    .d(RD2E),
    .q(WriteDataM)
  );

  flopr #(5) exmem_rdreg(
    .clk(clk),
    .reset(reset),
    .d(RdE),
    .q(RdM)
  );

  flopr #(WIDTH) exmem_pcplus4reg(
    .clk(clk),
    .reset(reset),
    .d(PCPlus4E),
    .q(PCPlus4M)
  );

  // MEM/WB pipeline register
  flopr #(WIDTH) memwb_aluresultreg(
    .clk(clk),
    .reset(reset),
    .d(ALUResultM),
    .q(ALUResultW)
  );

  flopr #(WIDTH) memwb_readdatareg(
    .clk(clk),
    .reset(reset),
    .d(ReadDataM),
    .q(ReadDataW)
  );

  flopr #(5) memwb_rdreg(
    .clk(clk),
    .reset(reset),
    .d(RdM),
    .q(RdW)
  );

  flopr #(WIDTH) memwb_pcplus4reg(
    .clk(clk),
    .reset(reset),
    .d(PCPlus4M),
    .q(PCPlus4W)
  );

  // Writeback stage
  mux3 #(WIDTH) resultmux(
    .d0(ALUResultW),
    .d1(ReadDataW),
    .d2(PCPlus4W),
    .s(ResultSrcW),
    .y(ResultW)
  );
endmodule
