#!/bin/bash
# run_all_gem5.sh — Run gem5 v25 stdlib simulation on all UlSWaP-Bench benchmarks
#
# Usage: bash run_all_gem5.sh [bench_dir] [output_dir]
#
# Defaults assume standard paths. Edit if yours differ.

GEM5="${GEM5:-$HOME/gem5/build/ALL/gem5.opt}"
CONFIG="$(dirname "$0")/../configs/run_gem5_stdlib.py"
BENCH_DIR="${1:-$HOME/gem5/UlSWaP-Bench/build_aarch64/bin}"
OUTPUT_DIR="${2:-$HOME/gem5/m5out_UlSWaP-Bench}"

mkdir -p "$OUTPUT_DIR"

TOTAL=$(ls "$BENCH_DIR"/*.elf 2>/dev/null | wc -l)
COUNT=0; OK=0; FAIL=0

echo ""
echo "============================================================"
echo "  gem5 v25 Batch Run — $TOTAL UlSWaP-Bench benchmarks"
echo "  Config: $CONFIG"
echo "============================================================"
echo ""

for elf in "$BENCH_DIR"/*.elf; do
    [ -f "$elf" ] || continue
    name=$(basename "$elf" .elf)
    outdir="$OUTPUT_DIR/m5out_${name}"
    COUNT=$((COUNT + 1))

    printf "[%2d/%d] %-20s " "$COUNT" "$TOTAL" "$name"
    $GEM5 -d "$outdir" "$CONFIG" "$elf" > /dev/null 2>&1

    if [ -f "$outdir/stats.txt" ]; then
        secs=$(grep "^simSeconds" "$outdir/stats.txt" | head -1 | awk '{print $2}')
        printf "OK  (%.6f s)\n" "$secs"
        OK=$((OK + 1))
    else
        printf "FAILED\n"
        FAIL=$((FAIL + 1))
    fi
done

echo ""
echo "============================================================"
echo "  Done: $OK/$TOTAL succeeded, $FAIL failed"
echo "  Output: $OUTPUT_DIR"
echo "============================================================"
