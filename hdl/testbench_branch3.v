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
      if (DataAdr === 32'd96 && WriteData === 32'd1)
        $display("BNE subset ok: Mem[96] = 1");
      else if (DataAdr === 32'd100 && WriteData === 32'd1)
        $display("BLT subset ok: Mem[100] = 1");
      else if (DataAdr === 32'd104 && WriteData === 32'd1)
        $display("BGE subset ok: Mem[104] = 1");
      else if (DataAdr === 32'd108 && WriteData === 32'd0) begin
        $display("Branch family subset succeeded");
        $finish;
      end else begin
        $display("Unexpected store: Adr=%0d Data=0x%08X", DataAdr, WriteData);
        $finish;
      end
    end
  end
endmodule
