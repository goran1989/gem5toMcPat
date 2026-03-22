#!/bin/bash
# run_all_mcpat.sh — Run McPAT on all parsed XML files
#
# Usage: bash run_all_mcpat.sh [xml_dir]

MCPAT="${MCPAT:-$HOME/Desktop/ext-grn/mcpat/mcpat-master/mcpat}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
XML_DIR="${1:-$SCRIPT_DIR/../parser/mcpat_xml_outputs}"
RESULT_DIR="$XML_DIR/mcpat_results"

mkdir -p "$RESULT_DIR"

echo ""
echo "============================================================"
echo "  McPAT Batch Run"
echo "============================================================"

# Fix L2 ordering first
echo "  Fixing XML L2 ordering..."
python3 "$SCRIPT_DIR/fix_xml_l2_order.py" "$XML_DIR"/mcpat_*.xml 2>/dev/null
echo ""

COUNT=0
for xml in "$XML_DIR"/mcpat_*.xml; do
    [ -f "$xml" ] || continue
    name=$(basename "$xml" .xml | sed 's/^mcpat_//')
    mkdir -p "$RESULT_DIR/$name"
    $MCPAT -infile "$xml" -print_level 5 > "$RESULT_DIR/$name/mcpat_output.txt" 2>&1
    COUNT=$((COUNT + 1))
    echo "  Done: $name"
done

echo ""
echo "  Processed: $COUNT benchmarks"
echo "  Results: $RESULT_DIR/"
echo "============================================================"
