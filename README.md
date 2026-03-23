# gem5toMcPat — gem5 v25+ Power Profiling Pipeline

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![gem5](https://img.shields.io/badge/gem5-v25.0+-green.svg)](https://www.gem5.org/)
[![McPAT](https://img.shields.io/badge/McPAT-v1.3-orange.svg)](https://github.com/HewlettPackard/mcpat)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-yellow.svg)](https://python.org)

**A complete, working pipeline to extract per-core power, energy, and execution time from gem5 v25+ simulations using McPAT — including the parser fix for gem5's new `board.processor.cores*` stat naming format.**

> **Problem:** gem5 v25 introduced stdlib-based configs that produce stat names like `board.processor.cores0.core.commitStats0.numInsts`. The widely-used [Gem5toMcPat parser](https://github.com/Hardik44/Gem5toMcPat_parser) expects classic `system.cpu0.*` names — resulting in **incompatibility issue** from McPAT.
>
> **Solution:** This repo provides a modified parser with a v25 stat-name translation layer, automation scripts, and a step-by-step workflow to go from benchmark ELFs → gem5 stats → McPAT power → energy tables.

---

## Table of Contents

- [Pipeline Overview](#pipeline-overview)
- [Quick Start](#quick-start)
- [Step-by-Step Guide](#step-by-step-guide)
- [Scripts Reference](#scripts-reference)
- [Stat Name Mapping](#stat-name-mapping)
- [Troubleshooting](#troubleshooting)
- [Output Examples](#output-examples)
- [Credits & Citation](#credits--citation)
- [License](#license)

---

## Pipeline Overview

```
 ┌──────────────────────────────┐
 │  1. Cross-Compile Benchmarks │  aarch64-linux-gnu-gcc -static
 │     (UlSWaP-Bench / MiBench) │  → 28 static AArch64 ELF binaries
 └──────────────┬───────────────┘
                ▼
 ┌──────────────────────────────┐
 │  2. gem5 v25 Simulation      │  configs/run_gem5_stdlib.py
 │     ARM O3, 4-core, 1.4 GHz  │  → stats.txt + config.json per benchmark
 └──────────────┬───────────────┘
                ▼
 ┌──────────────────────────────┐
 │  3. gem5 → McPAT Parser      │  parser/Program.py + writeStatValue_v25_fix.py
 │     (v25 stat name fix)      │  → McPAT-ready config.xml per benchmark
 └──────────────┬───────────────┘
                ▼
 ┌──────────────────────────────┐
 │  4. Fix XML Ordering         │  scripts/fix_xml_l2_order.py
 │     L2 caches before L30     │  (required for McPAT to accept the XML)
 └──────────────┬───────────────┘
                ▼
 ┌──────────────────────────────┐
 │  5. McPAT v1.3               │  → P_dyn, P_leak per core per benchmark
 └──────────────┬───────────────┘
                ▼
 ┌──────────────────────────────┐
 │  6. Extract Results          │  scripts/extract_wcet.sh
 │     eWCET, Power, Energy     │  scripts/extract_power.sh
 │                              │  E_task = P_total × eWCET
 └──────────────────────────────┘
```

---

## Quick Start

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/gem5toMcPat.git
cd gem5toMcPat

# 1. Run gem5 on one benchmark
cd ~/gem5
./build/ALL/gem5.opt -d m5out_aes configs/run_gem5_stdlib.py \
    ~/UlSWaP-Bench/build_aarch64/bin/aes.elf

# 2. Parse gem5 output → McPAT XML
cd gem5toMcPat/parser
python3 Program.py ~/gem5/m5out_aes/stats.txt ~/gem5/m5out_aes/config.json ARM_Template.xml

# 3. Fix XML ordering
python3 ../scripts/fix_xml_l2_order.py config.xml

# 4. Run McPAT
~/mcpat/mcpat -infile config.xml -print_level 5 > mcpat_output_aes.txt

# 5. Extract power (P_dyn from first Core: block)
grep -A5 "^Core:" mcpat_output_aes.txt | head -6
```

---

## Step-by-Step Guide

### Prerequisites

```bash
sudo apt install gcc-aarch64-linux-gnu build-essential python3 bc
```

You also need:
- **gem5 v25+** built with ARM ISA (`build/ALL/gem5.opt`)
- **McPAT v1.3** compiled ([HewlettPackard/mcpat](https://github.com/HewlettPackard/mcpat))

### Step 1: Cross-Compile Benchmarks

Using [UlSWaP-Bench](https://github.com/FoRTE-Research/UlSWaP-Bench) (28 embedded workloads: crypto, signal, image, IoT):

```bash
cd ~/UlSWaP-Bench
mkdir -p hw/aarch64_gem5
cp /path/to/gem5toMcPat/configs/aarch64_gem5_config.cmake hw/aarch64_gem5/config.cmake
cmake . -B build_aarch64 -DARCH=aarch64_gem5
cmake --build build_aarch64 -j$(nproc)

# Verify: should be 28 static ARM binaries
file build_aarch64/bin/*.elf | head -3
# aes.elf: ELF 64-bit LSB executable, ARM aarch64, statically linked
```

Or compile any C program manually:

```bash
aarch64-linux-gnu-gcc -static -O2 -o my_bench.elf my_bench.c
```

### Step 2: Run gem5 Simulation

**Single benchmark:**
```bash
cd ~/gem5
./build/ALL/gem5.opt -d m5out_aes \
    /path/to/gem5toMcPat/configs/run_gem5_stdlib.py \
    ~/UlSWaP-Bench/build_aarch64/bin/aes.elf
```

**All 28 benchmarks (batch):**
```bash
bash /path/to/gem5toMcPat/scripts/run_all_gem5.sh
```

Each benchmark produces `m5out_<name>/stats.txt` and `m5out_<name>/config.json`.

### Step 3: Parse gem5 Output → McPAT XML

**Single benchmark:**
```bash
cd /path/to/gem5toMcPat/parser
python3 Program.py /path/to/stats.txt /path/to/config.json ARM_Template.xml
# Output: config.xml
```

**All benchmarks (batch):**
```bash
bash scripts/run_all_parser.sh /path/to/m5out_benchmarks/
# Output: mcpat_xml_outputs/mcpat_<name>.xml for each benchmark
```

### Step 4: Fix XML Component Ordering

McPAT requires L2 cache components (`system.L20`–`system.L23`) to appear **before** `system.L30`, and `system.L2Directory0` to appear right after `system.L1Directory0`. The parser sometimes places them incorrectly.

```bash
python3 scripts/fix_xml_l2_order.py mcpat_xml_outputs/mcpat_*.xml
```

### Step 5: Run McPAT

**Single benchmark:**
```bash
mcpat -infile mcpat_aes.xml -print_level 5 > mcpat_output_aes.txt
```

**All benchmarks (batch):**
```bash
bash scripts/run_all_mcpat.sh mcpat_xml_outputs/
```

### Step 6: Extract Results

**eWCET table** (from gem5 stats):
```bash
bash scripts/extract_wcet.sh /path/to/m5out_benchmarks/ wcet_results.csv
```

**Power table** (from McPAT output):
```bash
bash scripts/extract_power.sh /path/to/mcpat_results/ power_results.csv
```

**Energy calculation:**
```
E_task = P_total × eWCET

Example (AES):
  P_dyn   = 1.130 W  (McPAT Runtime Dynamic)
  P_leak  = 0.135 W  (Subthreshold + Gate Leakage)
  P_total = 1.265 W
  eWCET   = 12.836 ms = 0.012836 s
  E_task  = 1.265 × 0.012836 = 16.24 mJ
```

---

## Scripts Reference

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/run_all_gem5.sh` | Run gem5 on all benchmarks | `bash run_all_gem5.sh` |
| `scripts/run_all_parser.sh` | Parse all gem5 outputs → McPAT XMLs | `bash run_all_parser.sh [m5out_dir]` |
| `scripts/run_all_mcpat.sh` | Run McPAT on all parsed XMLs | `bash run_all_mcpat.sh [xml_dir]` |
| `scripts/fix_xml_l2_order.py` | Fix L2/L2Directory/L30 ordering in XML | `python3 fix_xml_l2_order.py *.xml` |
| `scripts/extract_wcet.sh` | Extract eWCET, instructions, IPC table | `bash extract_wcet.sh [m5out_dir] [out.csv]` |
| `scripts/extract_power.sh` | Extract P_dyn, P_leak from McPAT results | `bash extract_power.sh [results_dir] [out.csv]` |

---

## Stat Name Mapping

The core contribution: translating 40+ gem5 v25 stat names to McPAT XML fields.

| McPAT Field | gem5 v25 stdlib Name |
|---|---|
| `total_instructions` | `board.processor.cores{N}.core.decode.decodedInsts` |
| `load_instructions` | `board.processor.cores{N}.core.commitStats0.numLoadInsts` |
| `store_instructions` | `board.processor.cores{N}.core.commitStats0.numStoreInsts` |
| `int_regfile_reads` | `board.processor.cores{N}.core.executeStats0.numIntRegReads` |
| `ROB_reads` | `board.processor.cores{N}.core.rob.reads` |
| `ialu_accesses` | `board.processor.cores{N}.core.intAluAccesses` |
| `icache.read_accesses` | `board.cache_hierarchy.l1i-cache-{N}.ReadReq.accesses::total` |
| `dcache.read_accesses` | `board.cache_hierarchy.l1d-cache-{N}.ReadReq.accesses::total` |

Full mapping: [docs/STAT_NAME_MAPPING.md](docs/STAT_NAME_MAPPING.md)

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Runtime Dynamic = 0 in McPAT | Parser can't read v25 stat names | Use this repo's `parser/Program.py` with `writeStatValue_v25_fix.py` |
| `KeyError: 0` in parser | Config has `system.cpu` not `system.cpu0` | Parser handles this; or `sed -i 's/system\.cpu\./system.cpu0./g' stats.txt` |
| "L2cache cannot satisfy constraint" | L2 config mismatch | Set `Private_L2=1` and `homogeneous_L2s=1` in config.xml |
| L2 components in wrong XML order | Parser ordering bug | `python3 scripts/fix_xml_l2_order.py config.xml` |
| Parser requires Python 2 | Using original parser | This repo's parser is Python 3 compatible |

Full guide: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

---

## Output Examples

### eWCET Table (28 UlSWaP-Bench benchmarks, gem5 ARM O3 @ 1.4 GHz)

```
Benchmark            eWCET (ms)     Instructions           Cycles      IPC
poly1305                 0.078         180,856         108,613     1.67
lzfx_decomp              0.080         186,201         112,418     1.67
aes                     12.836      40,639,748      17,977,222     2.26
ecc                     45.695     115,497,299      63,997,980     1.81
rsa                     85.243     279,011,890     119,387,804     2.34
```

### Power Table (McPAT results, Core 0)

```
Benchmark          P_dyn(W)   P_leak_sub   P_leak_gate  P_total(W)
aes                 1.1302     0.0696       0.0652        1.2650
dijkstra            0.6726     0.0696       0.0652        0.8074
rsa                 0.8934     0.0696       0.0652        1.0282
```

---

## Repository Structure

```
gem5toMcPat/
├── README.md
├── LICENSE
├── .gitignore
├── parser/                            # Modified gem5→McPAT parser
│   ├── Program.py                     # Main parser (Python 3, v25-aware)
│   ├── writeStatValue_v25_fix.py      # v25 stat name translation layer
│   ├── ARM_Template.xml               # McPAT ARM template
│   └── Xeon.xml                       # McPAT Xeon template
├── configs/                           # gem5 simulation configs
│   ├── run_gem5_stdlib.py             # gem5 v25 stdlib config (4-core ARM O3)
│   └── aarch64_gem5_config.cmake      # UlSWaP-Bench cross-compile config
├── scripts/                           # Automation & extraction
│   ├── run_all_gem5.sh                # Batch: gem5 on all benchmarks
│   ├── run_all_parser.sh              # Batch: parser on all results
│   ├── run_all_mcpat.sh               # Batch: McPAT on all XMLs
│   ├── fix_xml_l2_order.py            # Fix L2/L30 ordering in McPAT XML
│   ├── extract_wcet.sh                # Extract eWCET + CSV
│   └── extract_power.sh               # Extract power + CSV
├── docs/
│   ├── STAT_NAME_MAPPING.md           # Complete old→new stat name mapping
│   └── TROUBLESHOOTING.md             # Common errors and fixes
└── examples/
    └── hello_arm.c                    # Simple test program
```

---

## Tested Environment

| Component | Version |
|-----------|---------|
| gem5 | v25.0.0.1 (compiled Nov 2025) |
| McPAT | v1.3 (Feb 2015) |
| GCC Cross-compiler | aarch64-linux-gnu-gcc 13.x |
| OS | Ubuntu 22.04 / 24.04 |
| Python | 3.10+ |
| Benchmarks | [UlSWaP-Bench](https://github.com/FoRTE-Research/UlSWaP-Bench) (28 workloads) |

---

## Credits & Citation

### Acknowledgments

- **Original Parser:** [Hardik44/Gem5toMcPat_parser](https://github.com/Hardik44/Gem5toMcPat_parser) — the original gem5-to-McPAT parser that this work extends for v25 compatibility
- **Benchmarks:** [FoRTE-Research/UlSWaP-Bench](https://github.com/FoRTE-Research/UlSWaP-Bench) — embedded benchmark suite for SWaP-constrained systems
- **gem5 Simulator:** [gem5.org](https://www.gem5.org/) — cycle-accurate multicore architecture simulator
- **McPAT:** [HewlettPackard/mcpat](https://github.com/HewlettPackard/mcpat) — multicore power, area, and timing framework

### Citation

If you use this pipeline in your research, please cite:

```bibtex
@misc{gem5tomcpat_v25,
  author       = {Goran W. HamaAli and Diary R. Sulaiman},
  title        = {gem5toMcPat: Power Profiling Pipeline for gem5 v25+ with McPAT},
  year         = {2026},
  publisher    = {GitHub},
  url          = {https://github.com/goran1989/gem5toMcPat}
}
```

This tool was developed as part of the PhD program at Software and Informatics Department/College of Engineering/Salahaddin University-Erbil


---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

**Keywords:** gem5, McPAT, power profiling, energy estimation, multicore, ARM, real-time systems, task scheduling, WCET, embedded systems, thermal-aware scheduling, gem5 v25, stdlib, board-based config, stat name mapping, parser fix
