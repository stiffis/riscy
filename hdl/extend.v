module extend(input  [31:7] instr,
              input  [1:0]  immsrc,
              input  [6:0]  op,
              output [31:0] immext);
  
  reg [31:0] immext_reg;
  assign immext = immext_reg;

  always @* case(immsrc)
               2'b00:   immext_reg = {{20{instr[31]}}, instr[31:20]};
               2'b01:   immext_reg = {{20{instr[31]}}, instr[31:25], instr[11:7]};
               2'b10:   immext_reg = {{20{instr[31]}}, instr[7], instr[30:25], instr[11:8], 1'b0};
               2'b11:   if (op == 7'b0110111)
                           immext_reg = {instr[31:12], 12'b0}; // lui
                         else
                           immext_reg = {{12{instr[31]}}, instr[19:12], instr[20], instr[30:21], 1'b0}; // jal
      default: immext_reg = 32'bx;
    endcase
endmodule
