# aarch64_gem5_config.cmake
# Cross-compile UlSWaP-Bench for AArch64 gem5 SE-mode simulation
#
# Install:
#   mkdir -p UlSWaP-Bench/hw/aarch64_gem5
#   cp aarch64_gem5_config.cmake UlSWaP-Bench/hw/aarch64_gem5/config.cmake
#
# Build:
#   cd UlSWaP-Bench
#   cmake . -B build_aarch64 -DARCH=aarch64_gem5
#   cmake --build build_aarch64 -j$(nproc)
#
# Prerequisite:
#   sudo apt install gcc-aarch64-linux-gnu

function(set_aarch64_gem5_config)
    set(CMAKE_C_COMPILER "aarch64-linux-gnu-gcc" PARENT_SCOPE)
    set(CMAKE_ASM_COMPILER "aarch64-linux-gnu-gcc" PARENT_SCOPE)
    set(GENERAL_FLAGS "-static;-Wall;-g;-O2")
    set(ARCH_FLAGS "${GENERAL_FLAGS}" PARENT_SCOPE)
    set(ARCH_LINK_FLAGS "-static" PARENT_SCOPE)
    set(ARCH_OBJDUMP "aarch64-linux-gnu-objdump" PARENT_SCOPE)
endfunction()
