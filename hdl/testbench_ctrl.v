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
    #1200;
    $display("Simulation timed out");
    $finish;
  end

  always @(negedge clk) begin
    if (MemWrite) begin
      if (DataAdr === 32'd120 && WriteData === 32'd1)
        $display("BEQ control-flow subset ok: Mem[120] = 1");
      else if (DataAdr === 32'd124 && WriteData === 32'd80)
        $display("JAL link subset ok: Mem[124] = 80");
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
