/*
 * hello_arm.c — Simple test for gem5 ARM SE-mode simulation
 *
 * Compile:
 *   aarch64-linux-gnu-gcc -static -O2 -o hello_arm.elf hello_arm.c -lm
 *
 * Run in gem5:
 *   ./build/ALL/gem5.opt -d m5out_hello configs/run_gem5_stdlib.py hello_arm.elf
 */
#include <stdio.h>
#include <math.h>

int main() {
    printf("Hello from ARM gem5!\n");

    /* Integer ALU work */
    volatile long sum = 0;
    for (int i = 0; i < 100000; i++)
        sum += (long)i * i;
    printf("Integer sum = %ld\n", sum);

    /* Floating-point work */
    volatile double fsum = 0.0;
    for (int i = 1; i <= 10000; i++)
        fsum += sin((double)i * 0.001);
    printf("FP sum = %f\n", fsum);

    /* Memory access work */
    int arr[1024];
    for (int i = 0; i < 1024; i++) arr[i] = i * 3;
    long msum = 0;
    for (int i = 0; i < 1024; i++) msum += arr[i];
    printf("Mem sum = %ld\n", msum);

    printf("Done.\n");
    return 0;
}
