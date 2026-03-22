# Troubleshooting

## Runtime Dynamic = 0 for all McPAT components

**Cause:** The parser couldn't read gem5 v25 stat names.

**Fix:** Make sure you're using the `parser/Program.py` from this repo, which imports `writeStatValue_v25_fix.py`. The fix translates `board.processor.cores*` names to the format McPAT expects.

**Verify:** Open the generated `config.xml` and search for `total_instructions`. If it's 0, the translation didn't work.

## Parser error: `KeyError: 0` on `system.cpu0.isa.type`

**Cause:** gem5 v25 config.json uses `board.processor.cores` structure, not `system.cpu0`.

**Fix:** The parser's `getConfValue()` function handles this translation. Make sure you're using the full `Program.py` from this repo.

## McPAT warning: "L2cache cannot satisfy throughput/latency constraint"

**Cause:** The ARM template L2 parameters don't exactly match your gem5 config.

**Impact:** Usually cosmetic — McPAT still produces valid power numbers. Can be suppressed by adjusting L2 parameters in the template XML.

## McPAT error: "number_of_L2s is not correct"

**Cause:** L2 count in XML doesn't match the template expectation.

**Fix:** Open `config.xml` and verify:
```xml
<param name="Private_L2" value="1" />
<param name="homogeneous_L2s" value="1" />
<param name="number_of_L2s" value="4" />
```

## L2 components appear in wrong order in XML

**Cause:** The parser inserts L2 cache components after L30 instead of before.

**Fix:**
```bash
python3 scripts/fix_xml_l2_order.py config.xml
```

This ensures: `L1Directory0 → L2Directory0 → L20..L23 → L30 → NoC0 → mc`

## Parser requires Python 2

**Cause:** You're using the original parser from [Hardik44/Gem5toMcPat_parser](https://github.com/Hardik44/Gem5toMcPat_parser).

**Fix:** Use the `parser/Program.py` from this repo — it's Python 3 compatible.

If you need to convert another parser:
```bash
2to3 -w Program.py
```

## gem5 error: "Couldn't find appropriate workload object"

**Cause:** Missing `SEWorkload.init_compatible()` call in gem5 v25 config.

**Fix:** Already handled in `configs/run_gem5_stdlib.py`. If writing custom configs, add:
```python
system.workload = SEWorkload.init_compatible(binary_path)
```

## Benchmarks must be statically linked

**Cause:** gem5 SE mode doesn't support dynamic linking.

**Fix:** Compile with `-static`:
```bash
aarch64-linux-gnu-gcc -static -O2 -o bench.elf bench.c
```

The provided `configs/aarch64_gem5_config.cmake` already includes `-static`.

## UlSWaP-Bench CMake error: "Unknown CMake command set_aarch64_gem5_config"

**Cause:** The function name in `config.cmake` must match the directory name exactly.

**Fix:** If your directory is `hw/aarch64_gem5/`, the function must be named `set_aarch64_gem5_config` (not `configure`). Use the provided `configs/aarch64_gem5_config.cmake`.
