start:
	addi s0, x0, 1000
	nop
	addi t0, x0, 10
	sw   t0, 0(s0)
	nop
	addi t0, x0, 20
	sw   t0, 4(s0)
	nop
	addi t0, x0, 30
	sw   t0, 8(s0)
	nop
	addi t0, x0, 40
	sw   t0, 12(s0)

#end:
# jal x0, end
