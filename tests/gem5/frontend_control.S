/* Freestanding regression for branch ownership across an x86 SIMD micro-op. */
.section .rodata
.p2align 4
payload:
    .byte 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16
result:
    .ascii "frontend-control: PASS\n"
.set result_length, . - result

.section .text
.global _start
_start:
    movdqa payload(%rip), %xmm3
    psrldq $15, %xmm3
    movq %xmm3, %rax
    cmp $16, %rax
    jne failure
    mov $1, %eax
    mov $1, %edi
    lea result(%rip), %rsi
    mov $result_length, %edx
    syscall
    xor %edi, %edi
    jmp exit
failure:
    mov $1, %edi
exit:
    mov $60, %eax
    syscall

.section .note.GNU-stack,"",@progbits
