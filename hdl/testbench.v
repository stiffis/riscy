module testbench;
  reg         clk;
  reg         reset;
  wire [31:0] WriteData;
  wire [31:0] DataAdr;
  wire        MemWrite;

  top dut(
    .clk(clk),
    .reset(reset),
    .WriteData(WriteData),
    .DataAdr(DataAdr),
    .MemWrite(MemWrite)
  );

  initial begin
    reset = 1;
    #22;
    reset = 0;
  end

  always begin
    clk = 1;
    #5;
    clk = 0;
    #5;
  end

  initial begin
    #2000;
    $display("Simulation timed out");
    $finish;
  end

  always @(negedge clk) begin
    if (MemWrite) begin
      if (DataAdr === 32'd96 && WriteData === 32'd7)
        $display("Intermediate store ok: Mem[96] = 7");
      else if (DataAdr === 32'd100 && WriteData === 32'd14)
        $display("Arithmetic subset ok: Mem[100] = 14");
      else if (DataAdr === 32'd104 && WriteData === 32'd15)
        $display("Logical OR subset ok: Mem[104] = 15");
      else if (DataAdr === 32'd108 && WriteData === 32'd7)
        $display("Logical AND subset ok: Mem[108] = 7");
      else if (DataAdr === 32'd112 && WriteData === 32'd1)
        $display("SLTI subset ok: Mem[112] = 1");
      else if (DataAdr === 32'd116 && WriteData === 32'd1)
        $display("SLT subset ok: Mem[116] = 1");
      else if (DataAdr === 32'd120 && WriteData === 32'd1)
        $display("BEQ control-flow subset ok: Mem[120] = 1");
      else if (DataAdr === 32'd124 && WriteData === 32'd252)
        $display("JAL link subset ok: Mem[124] = 252");
      else if (DataAdr === 32'd128 && WriteData === 32'd0) begin
        $display("Pipeline control subset succeeded");
        $finish;
      end else begin
        $display("Unexpected store: Adr=%0d Data=%0d", DataAdr, WriteData);
        $finish;
      end
    end
  end
endmodule
