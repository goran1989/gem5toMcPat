"""
run_gem5_stdlib.py — gem5 v25 stdlib config for ARM O3 multicore SE simulation

Uses gem5's standard library (SimpleBoard + SimpleProcessor).
Produces board.processor.cores*.core.* stat names.
The parser/Program.py + writeStatValue_v25_fix.py handles the translation.

Usage:
    cd ~/gem5
    ./build/ALL/gem5.opt -d m5out_aes run_gem5_stdlib.py /path/to/aes.elf

Platform: gem5 v25.0+ with ALL ISA build
"""

import sys
import os

from gem5.components.boards.simple_board import SimpleBoard
from gem5.components.cachehierarchies.classic.private_l1_private_l2_cache_hierarchy import (
    PrivateL1PrivateL2CacheHierarchy,
)
from gem5.components.memory.single_channel import SingleChannelDDR4_2400
from gem5.components.processors.cpu_types import CPUTypes
from gem5.components.processors.simple_processor import SimpleProcessor
from gem5.isas import ISA
from gem5.resources.resource import BinaryResource
from gem5.simulate.simulator import Simulator

if len(sys.argv) < 2:
    print("Usage: gem5.opt run_gem5_stdlib.py <path/to/arm_binary.elf>")
    sys.exit(1)

bench_path = sys.argv[1]
if not os.path.exists(bench_path):
    print(f"ERROR: Binary not found: {bench_path}")
    sys.exit(1)

name = os.path.basename(bench_path).replace(".elf", "")

# --- Cache Hierarchy ---
cache_hierarchy = PrivateL1PrivateL2CacheHierarchy(
    l1d_size="32KiB",
    l1i_size="32KiB",
    l2_size="2MiB",
)

# --- Memory ---
memory = SingleChannelDDR4_2400(size="4GiB")

# --- Processor: 4-core ARM O3 ---
processor = SimpleProcessor(
    cpu_type=CPUTypes.O3,
    isa=ISA.ARM,
    num_cores=4,
)

# --- Board ---
board = SimpleBoard(
    clk_freq="1.4GHz",
    processor=processor,
    memory=memory,
    cache_hierarchy=cache_hierarchy,
)

# --- Workload ---
board.set_se_binary_workload(
    BinaryResource(local_path=bench_path),
)

# --- Run ---
simulator = Simulator(board=board)
print(f"\n{'='*60}")
print(f"  {name} | ARM O3 x4 @ 1.4GHz | gem5 v25 stdlib")
print(f"  L1I: 32KB | L1D: 32KB | L2: 2MB private")
print(f"{'='*60}\n")

simulator.run()
print(f"\n  {name} complete!")
