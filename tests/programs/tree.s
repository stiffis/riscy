.global _start
_start:
	li		sp, 0x10000
    li		a0, 0x1000

    li		t1, 6
    sw 		t1, 0(a0)
    li 		t1, 4
    sw 		t1, 4(a0)
    li 		t1, 4
    sw 		t1, 8(a0)
    li 		t1, 1
    sw 		t1, 12(a0)
    li 		t1, 2
    sw 		t1, 16(a0)
    li 		t1, 2
    sw 		t1, 20(a0)
    li 		t1, 1
    sw 		t1, 24(a0)

    li		a1, 7
	call	is_symmetric

	j		.

is_symmetric:
	bne		a0, zero, no_early_return
	li		a0, 1
	ret

# a0: int arr[]
# a1: size_t n
no_early_return:
	li		a2, 1
	li		a3, 2
	j		solve

# a0: int arr[]
# a1: size_t n
# a2: size_t l
# a3: size_t r
solve:
	blt		a2, a1, no_early_return_1
		# if (l >= n)
		li		a0, 1
		ret
no_early_return_1:

	blt		a3, a1, no_early_return_2
		# if (r >= n)
		li		a0, 0
		ret
no_early_return_2:

	slli	t0, a2, 2
	add		t0, t0, a0 # t0 <- &arr[l]
	lw		t0, 0(t0)  # t0 <-  arr[l]

	slli	t1, a3, 2
	add		t1, t1, a0 # t0 <- &arr[r]
	lw		t1, 0(t1)  # t0 <-  arr[r]

	beq		t0, t1, cond_1_true
	li		a0, 0
	ret

cond_1_true:

	addi	sp, sp, -32
	sw		ra, 28(sp)
	sw		s0, 24(sp)
	sw		s1, 20(sp)
	sw		s2, 16(sp)
	sw		s3, 12(sp)

	add		a2, a2, a2 # a2 *= 2
	addi	a2, a2, 1  # a2 <- 2*l + 1

	add		a3, a3, a3 # a3 *= 2
	addi	a3, a3, 2  # a3 <- 2*r + 2

	mv		s0, a0 # s0 <- arr
	mv		s1, a1 # s1 <- n
	mv		s2, a2 # s2 <- 2*l + 1
	mv		s3, a3 # s3 <- 2*r + 2

	call	solve

	bne		a0, zero, cond_2_true
	j		epilogue

cond_2_true:

	mv		a0, s0
	mv		a1, s1
	addi	a2, s2, 1
	addi	a3, s3, -1
	call	solve
	# a0 <- solve(arr, n, 2*l + 2, 2*r + 1)

epilogue:
	lw		ra, 28(sp)
	lw		s0, 24(sp)
	lw		s1, 20(sp)
	lw		s2, 16(sp)
	lw		s3, 12(sp)
	addi	sp, sp, 32
	ret
