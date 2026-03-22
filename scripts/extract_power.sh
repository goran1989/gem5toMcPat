#!/bin/bash
# extract_power.sh — Extract power data from McPAT output files
#
# Extracts Runtime Dynamic, Subthreshold Leakage, Gate Leakage from
# the FIRST Core: block (between "Core:" and "Instruction Fetch Unit:")
#
# Supports three layouts:
#   1. results_dir/mcpat_output_aes.txt        (flat, prefixed)
#   2. results_dir/result_aes.txt              (flat, prefixed)
#   3. results_dir/aes/mcpat_output.txt        (subdirectory)
#
# Usage: bash extract_power.sh [results_dir] [output.csv]

RESULT_DIR="${1:-.}"
CSV_FILE="${2:-power_results.csv}"

echo "Benchmark,P_dyn_W,P_leak_sub_W,P_leak_gate_W,P_total_W" > "$CSV_FILE"

printf "\n%-20s %10s %12s %12s %10s\n" "Benchmark" "P_dyn(W)" "P_leak_sub" "P_leak_gate" "P_total(W)"
printf "%-20s %10s %12s %12s %10s\n" "--------------------" "----------" "------------" "------------" "----------"

extract_from_file() {
    local f="$1" name="$2"

    core_line=$(grep -n "^Core:" "$f" | head -1 | cut -d: -f1)
    [ -z "$core_line" ] && return

    fetch_line=$(tail -n +"$core_line" "$f" | grep -n "Instruction Fetch Unit:" | head -1 | cut -d: -f1)
    [ -z "$fetch_line" ] && return

    end_line=$((core_line + fetch_line - 2))
    block=$(sed -n "${core_line},${end_line}p" "$f")

    runtime=$(echo "$block" | grep "Runtime Dynamic" | awk '{print $(NF-1)}')
    sub_leak=$(echo "$block" | grep "Subthreshold Leakage" | awk '{print $(NF-1)}')
    gate_leak=$(echo "$block" | grep "Gate Leakage" | awk '{print $(NF-1)}')

    [ -z "$runtime" ] && return

    p_total=$(echo "$runtime + $sub_leak + $gate_leak" | bc -l 2>/dev/null || echo "0")

    printf "%-20s %10s %12s %12s %10.6f\n" "$name" "$runtime" "$sub_leak" "$gate_leak" "$p_total"
    echo "$name,$runtime,$sub_leak,$gate_leak,$p_total" >> "$CSV_FILE"
}

# Detect layout and process
found=0

# Layout 1: mcpat_output_*.txt
for f in "$RESULT_DIR"/mcpat_output_*.txt; do
    [ -f "$f" ] || continue
    name=$(basename "$f" .txt | sed 's/^mcpat_output_//')
    extract_from_file "$f" "$name"
    found=1
done

# Layout 2: result_*.txt
if [ "$found" -eq 0 ]; then
    for f in "$RESULT_DIR"/result_*.txt; do
        [ -f "$f" ] || continue
        name=$(basename "$f" .txt | sed 's/^result_//')
        extract_from_file "$f" "$name"
        found=1
    done
fi

# Layout 3: subdirectories
if [ "$found" -eq 0 ]; then
    for dir in "$RESULT_DIR"/*/; do
        f="$dir/mcpat_output.txt"
        [ -f "$f" ] || continue
        name=$(basename "$dir")
        extract_from_file "$f" "$name"
        found=1
    done
fi

if [ "$found" -eq 0 ]; then
    echo "No McPAT output files found in: $RESULT_DIR"
    echo "Expected: mcpat_output_*.txt, result_*.txt, or */mcpat_output.txt"
    exit 1
fi

printf "\nCSV saved: %s (%d benchmarks)\n\n" "$CSV_FILE" "$(tail -n +2 "$CSV_FILE" | wc -l)"
