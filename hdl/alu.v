module alu(input  [31:0] a, b,
           input  [3:0]  alucontrol,
           output [31:0] result,
           output zero);
  
  wire [31:0] condinvb, sum;
  wire        v;
  wire        isAddSub;

  reg [31:0] result_reg;
  assign result = result_reg;

  assign condinvb = alucontrol[0] ? ~b : b;
  assign sum = a + condinvb + alucontrol[0];
  assign isAddSub = (~alucontrol[3] & ~alucontrol[2] & ~alucontrol[1]) |
                    (~alucontrol[3] & ~alucontrol[2] & alucontrol[0]);

  always @* case (alucontrol)
      4'b0000: result_reg = sum; // add
      4'b0001: result_reg = sum; // subtract
      4'b0010: result_reg = a & b; // and
      4'b0011: result_reg = a | b; // or
      4'b0100: result_reg = a ^ b; // xor
      4'b0101: result_reg = sum[31] ^ v; // slt
      4'b0110: result_reg = b; // lui pass-through immediate
      4'b0111: result_reg = a << b[4:0]; // sll
      4'b1000: result_reg = a >> b[4:0]; // srl
      4'b1001: result_reg = $signed(a) >>> b[4:0]; // sra
      default: result_reg = 32'bx;
    endcase

  assign zero = (result == 32'b0);
  assign v = ~(alucontrol[0] ^ a[31] ^ b[31]) & (a[31] ^ sum[31]) & isAddSub;
endmodule
