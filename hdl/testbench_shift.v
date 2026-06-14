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
      if (DataAdr === 32'd96 && WriteData === 32'd12)
        $display("SLLI subset ok: Mem[96] = 12");
      else if (DataAdr === 32'd100 && WriteData === 32'd6)
        $display("SLL subset ok: Mem[100] = 6");
      else if (DataAdr === 32'd104 && WriteData === 32'd4)
        $display("SRLI subset ok: Mem[104] = 4");
      else if (DataAdr === 32'd108 && WriteData === 32'd16)
        $display("SRL subset ok: Mem[108] = 16");
      else if (DataAdr === 32'd112 && WriteData === 32'hFFFFFFFC)
        $display("SRAI subset ok: Mem[112] = 0xFFFFFFFC");
      else if (DataAdr === 32'd116 && WriteData === 32'hFFFFFFFC) begin
        $display("Shift subset succeeded");
        $finish;
      end else begin
        $display("Unexpected store: Adr=%0d Data=0x%08X", DataAdr, WriteData);
        $finish;
      end
    end
  end
endmodule
