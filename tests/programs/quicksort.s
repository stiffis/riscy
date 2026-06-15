.global _start
_start:
	li		sp, 0x10000
    li		a0, 0x1000

    li		t1, 6
    sw 		t1, 0(a0)
    li 		t1, 4
    sw 		t1, 4(a0)
    li 		t1, 3
    sw 		t1, 8(a0)
    li 		t1, 2
    sw 		t1, 12(a0)
    li 		t1, 1
    sw 		t1, 16(a0)
    li 		t1, 8
    sw 		t1, 20(a0)
    li 		t1, 9
    sw 		t1, 24(a0)

    li		a1, 0
    li 		a2, 7
    call	_qsort

_end:
    j _end

# a0: int arr[]
# a1: size_t l
# a2: size_t r
_qsort:
    bge		a1, a2, _qsort_end

    addi	sp, sp, -16
    sw		ra, 12(sp)
    sw		s0, 8(sp)
    sw		s1, 4(sp)
    sw		s2, 0(sp)

	mv		s0, a0
	mv		s1, a1
	mv		s2, a2

    call	_partition
	# Ahora a0 contiene q

	mv		a2, a0
	mv		a1, s1
	mv		s1, a0 # s1 ahora guardará q
	mv		a0, s0
    call	_qsort # qsort(arr, l, q)

	mv		a2, s2
	addi	a1, s1, 1
	mv		a0, s0
    call	_qsort # qsort(arr, q + 1, r)

	lw		ra, 12(sp)
	lw		s0, 8(sp)
	lw		s1, 4(sp)
	lw		s2, 0(sp)
	addi	sp, sp, 16

_qsort_end:
    ret

# a0: int arr[]
# a1: size_t l
# a2: size_t r
_partition:
	# t0 <- pivot (arr[r - 1])
    slli t0, a2, 2
    add t0, a0, t0
    lw t0, -4(t0)

    # a1 <- q

    mv t1, a1 # t1 <- i
_for_begin:
        bge t1, a2, _for_end

        slli t2, t1, 2
        add t2, a0, t2 # t2 <- &arr[i]
        lw t3, 0(t2)   # t3 <- arr[i]

        blt t0, t3, _if_end
    _if_begin:
            slli t4, a1, 2
            add t4, a0, t4 # t4 <- &arr[q]
            lw t5, 0(t4)   # t5 <- arr[q]

            sw t5, 0(t2)
            sw t3, 0(t4)

            addi a1, a1, 1
    _if_end:

        addi t1, t1, 1
        j _for_begin
_for_end:

    addi a0, a1, -1
    ret
