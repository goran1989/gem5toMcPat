#!/bin/bash
# extract_wcet.sh — Extract eWCET, instructions, cycles, IPC from gem5 stats
#
# Usage: bash extract_wcet.sh [m5out_dir] [output.csv]

BASE_DIR="${1:-$HOME/gem5/m5out_UlSWaP-Bench}"
CSV_FILE="${2:-benchmark_wcet_results.csv}"

echo "Benchmark,eWCET_seconds,eWCET_ms,Instructions,Cycles,IPC" > "$CSV_FILE"

printf "\n%-20s %12s %16s %16s %8s\n" "Benchmark" "eWCET (ms)" "Instructions" "Cycles" "IPC"
printf "%-20s %12s %16s %16s %8s\n" "--------------------" "------------" "----------------" "----------------" "--------"

for dir in "$BASE_DIR"/m5out_*/; do
    stats="$dir/stats.txt"; [ -f "$stats" ] || continue
    name=$(basename "$dir" | sed 's/^m5out_//')

    sim_sec=$(grep "^simSeconds" "$stats" | head -1 | awk '{print $2}')
    sim_insts=$(grep "^simInsts" "$stats" | head -1 | awk '{print $2}')
    cycles=$(grep -E "core\.numCycles|cpu0*\.numCycles" "$stats" | head -1 | awk '{print $2}')
    ipc=$(grep -E "core\.ipc|cpu0*\.ipc " "$stats" | head -1 | awk '{print $2}')

    [ -n "$sim_sec" ] && wcet_ms=$(echo "$sim_sec * 1000" | bc -l | xargs printf "%.3f") || wcet_ms="N/A"
    [ -n "$sim_insts" ] && insts_fmt=$(printf "%'d" "$sim_insts" 2>/dev/null) || insts_fmt="N/A"
    [ -n "$cycles" ] && cycles_fmt=$(printf "%'d" "$cycles" 2>/dev/null) || cycles_fmt="N/A"
    [ -n "$ipc" ] && ipc_fmt=$(printf "%.2f" "$ipc") || ipc_fmt="N/A"

    printf "%-20s %12s %16s %16s %8s\n" "$name" "$wcet_ms" "$insts_fmt" "$cycles_fmt" "$ipc_fmt"
    echo "$name,${sim_sec:-N/A},$wcet_ms,${sim_insts:-N/A},${cycles:-N/A},${ipc:-N/A}" >> "$CSV_FILE"
done

printf "\nCSV saved: %s (%d benchmarks)\n\n" "$CSV_FILE" "$(tail -n +2 "$CSV_FILE" | wc -l)"
