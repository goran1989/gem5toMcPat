#!/bin/bash
# run_all_parser.sh — Run gem5→McPAT parser on all benchmark results
#
# Usage: bash run_all_parser.sh [m5out_dir] [output_dir]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PARSER_DIR="$SCRIPT_DIR/../parser"
PARSER="$PARSER_DIR/Program.py"
TEMPLATE="$PARSER_DIR/ARM_Template.xml"
M5OUT_DIR="${1:-$HOME/gem5/m5out_UlSWaP-Bench}"
OUTPUT_DIR="${2:-$PARSER_DIR/mcpat_xml_outputs}"

mkdir -p "$OUTPUT_DIR"

echo ""
echo "============================================================"
echo "  gem5 → McPAT Parser Batch Run"
echo "============================================================"

SUCCESS=0; FAILED=0

printf "%-25s %s\n" "Benchmark" "Status"
printf "%-25s %s\n" "-------------------------" "----------"

for dir in "$M5OUT_DIR"/m5out_*/; do
    [ -d "$dir" ] || continue
    name=$(basename "$dir" | sed 's/^m5out_//')
    stats="$dir/stats.txt"
    config="$dir/config.json"

    if [ ! -f "$stats" ] || [ ! -f "$config" ]; then
        printf "%-25s %s\n" "$name" "SKIP (missing files)"
        continue
    fi

    cd "$PARSER_DIR"
    python3 "$PARSER" "$stats" "$config" "$TEMPLATE" > /dev/null 2>&1

    if [ -f "$PARSER_DIR/config.xml" ]; then
        cp "$PARSER_DIR/config.xml" "$OUTPUT_DIR/mcpat_${name}.xml"
        printf "%-25s %s\n" "$name" "OK"
        SUCCESS=$((SUCCESS + 1))
    else
        printf "%-25s %s\n" "$name" "FAILED"
        FAILED=$((FAILED + 1))
    fi
done

echo ""
echo "  Successful: $SUCCESS | Failed: $FAILED"
echo "  Output: $OUTPUT_DIR"
echo "============================================================"
