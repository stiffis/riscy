module controller(input  clk, reset,
                  input  [6:0] opD,
                  input  [2:0] funct3D,
                  input  funct7b5D,
                  input  ZeroE,
                  input  CondBitE,
                  output [1:0] ResultSrcW,
                  output MemWriteM,
                  output PCSrcE, ALUSrcE,
                  output JalrE,
                  output RegWriteW,
                  output [1:0] ImmSrcD,
                  output [3:0] ALUControlE);
  
  wire [1:0] ResultSrcD, ResultSrcE, ResultSrcM;
  wire [1:0] ALUOpD;
  wire       BranchD, BranchE;
  wire [2:0] funct3E;
  wire       ALUSrcD;
  wire       RegWriteD, RegWriteE, RegWriteM;
  wire       JumpD, JumpE;
  wire       JalrD;
  wire       MemWriteD, MemWriteE;
  wire [3:0] ALUControlD;
  wire [11:0] controlsE_in, controlsE;
  wire [3:0] controlsM_in, controlsM;
  wire [2:0] controlsW_in, controlsW;

  maindec md(
    .op(opD),
    .ResultSrc(ResultSrcD),
    .MemWrite(MemWriteD),
    .Branch(BranchD),
    .ALUSrc(ALUSrcD),
    .RegWrite(RegWriteD),
    .Jump(JumpD),
    .Jalr(JalrD),
    .ImmSrc(ImmSrcD),
    .ALUOp(ALUOpD)
  );

  aludec ad(
    .opb5(opD[5]),
    .funct3(funct3D),
    .funct7b5(funct7b5D),
    .ALUOp(ALUOpD),
    .ALUControl(ALUControlD)
  );

  assign controlsE_in = {RegWriteD, ResultSrcD, MemWriteD, JumpD, JalrD,
                         BranchD, ALUControlD, ALUSrcD};

  flopr #(12) regE(
    .clk(clk),
    .reset(reset),
    .d(controlsE_in),
    .q(controlsE)
  );

  flopr #(3) funct3Ereg(
    .clk(clk),
    .reset(reset),
    .d(funct3D),
    .q(funct3E)
  );

  assign {RegWriteE, ResultSrcE, MemWriteE, JumpE, JalrE,
          BranchE, ALUControlE, ALUSrcE} = controlsE;

  assign PCSrcE = JumpE | JalrE |
                  (BranchE & (
                    (funct3E == 3'b000 && ZeroE) |
                    (funct3E == 3'b001 && ~ZeroE) |
                    (funct3E == 3'b100 && CondBitE) |
                    (funct3E == 3'b101 && ~CondBitE)
                  ));

  assign controlsM_in = {RegWriteE, ResultSrcE, MemWriteE};

  flopr #(4) regM(
    .clk(clk),
    .reset(reset),
    .d(controlsM_in),
    .q(controlsM)
  );

  assign {RegWriteM, ResultSrcM, MemWriteM} = controlsM;

  assign controlsW_in = {RegWriteM, ResultSrcM};

  flopr #(3) regW(
    .clk(clk),
    .reset(reset),
    .d(controlsW_in),
    .q(controlsW)
  );

  assign {RegWriteW, ResultSrcW} = controlsW;
endmodule
