#!/usr/bin/env python3
"""
fix_xml_l2_order.py — Fix component ordering in McPAT config XML

McPAT requires this exact order under <component id="system">:
    core0..core3 → L1Directory0 → L2Directory0 → L20..L23 → L30 → NoC0 → mc → ...

The parser sometimes places L2Directory0 and L20-L23 in wrong positions.
This script fixes both issues.

Usage:
    python3 fix_xml_l2_order.py config.xml
    python3 fix_xml_l2_order.py mcpat_xml_outputs/mcpat_*.xml
"""

import xml.etree.ElementTree as ET
import sys
import glob


def fix_xml(filepath):
    tree = ET.parse(filepath)
    root = tree.getroot()
    sys_comp = root.find('.//component[@id="system"]')
    if sys_comp is None:
        print(f"  Skip: {filepath} — no system component")
        return False

    children = list(sys_comp)

    # Identify elements by id
    l2_caches = [c for c in children
                 if c.attrib.get('id', '').startswith('system.L2')
                 and c.attrib.get('id') != 'system.L2Directory0']
    l30_list = [c for c in children if c.attrib.get('id') == 'system.L30']
    l2dir_list = [c for c in children if c.attrib.get('id') == 'system.L2Directory0']
    l1dir_list = [c for c in children if c.attrib.get('id') == 'system.L1Directory0']

    if not l2_caches or not l30_list:
        print(f"  Skip: {filepath} — no L2 caches or L30 found")
        return False

    changed = False

    # Step 1: Remove L2 caches from current positions
    for l2 in l2_caches:
        sys_comp.remove(l2)
        changed = True

    # Step 2: Fix L2Directory0 position — must be right after L1Directory0
    if l2dir_list and l1dir_list:
        sys_comp.remove(l2dir_list[0])
        l1dir_idx = list(sys_comp).index(l1dir_list[0])
        sys_comp.insert(l1dir_idx + 1, l2dir_list[0])
        changed = True

    # Step 3: Insert L20-L23 right before L30
    l30_idx = list(sys_comp).index(l30_list[0])
    for i, l2 in enumerate(sorted(l2_caches, key=lambda x: x.attrib['id'])):
        sys_comp.insert(l30_idx + i, l2)
        changed = True

    if changed:
        tree.write(filepath, xml_declaration=True)
        print(f"  Fixed: {filepath}")
        return True
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 fix_xml_l2_order.py <config.xml> [more files...]")
        sys.exit(1)

    files = []
    for arg in sys.argv[1:]:
        files.extend(glob.glob(arg))

    if not files:
        print("No files matched.")
        sys.exit(1)

    fixed = 0
    for f in sorted(set(files)):
        if fix_xml(f):
            fixed += 1

    print(f"\nFixed {fixed}/{len(files)} files")
