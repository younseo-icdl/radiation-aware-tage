/* Freestanding Linux x86-64 regression workload, with no libc dependency. */
#include <stdint.h>

static long syscall3(long n, long a, long b, long c) {
    long result;
    __asm__ volatile("syscall" : "=a"(result) : "a"(n), "D"(a), "S"(b), "d"(c) : "rcx", "r11", "memory");
    return result;
}

__attribute__((noreturn)) void _start(void) {
    volatile uint64_t state = 548;
    for (unsigned i = 0; i < 10000; ++i) {
        uint64_t x = state;
        state = (i % 7 < 3) ? (x * 6364136223846793005ULL + i) : ((x >> 3) ^ (x << 7) ^ i);
    }
    const char hex[] = "0123456789abcdef";
    char output[26] = "checksum: ";
    uint64_t result = state;
    for (unsigned i = 0; i < 16; ++i) output[10+i] = hex[(result >> (60-4*i)) & 15];
    syscall3(1, 1, (long)output, sizeof(output));
    syscall3(1, 1, (long)"\n", 1);
    syscall3(60, 0, 0, 0);
    __builtin_unreachable();
}
