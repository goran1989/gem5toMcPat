# gem5 v25 → McPAT Stat Name Mapping

Complete mapping between gem5 v25 stdlib stat names and the classic format expected by McPAT parsers.

## Core Pipeline

| McPAT XML Field | gem5 Classic (v20–v21) | gem5 v25 stdlib |
|---|---|---|
| `total_instructions` | `system.cpu0.decode.DecodedInsts` | `board.processor.cores0.core.decode.decodedInsts` |
| `int_instructions` | `system.cpu0.commit.int_insts` | `board.processor.cores0.core.commitStats0.numIntInsts` |
| `fp_instructions` | `system.cpu0.commit.fp_insts` | `board.processor.cores0.core.commitStats0.numFpInsts` |
| `load_instructions` | `system.cpu0.num_load_insts` | `board.processor.cores0.core.commitStats0.numLoadInsts` |
| `store_instructions` | `system.cpu0.num_store_insts` | `board.processor.cores0.core.commitStats0.numStoreInsts` |
| `committed_instructions` | `system.cpu0.committedInsts` | `board.processor.cores0.core.commitStats0.numInsts` |
| `branch_instructions` | `system.cpu0.branchPred.condPredicted` | `board.processor.cores0.core.branchPred.condPredicted` |
| `branch_mispredictions` | `system.cpu0.branchPred.condIncorrect` | `board.processor.cores0.core.branchPred.condIncorrect` |
| `total_cycles` | `system.cpu0.numCycles` | `board.processor.cores0.core.numCycles` |
| `pipeline_duty_cycle` | `system.cpu0.ipc_total` | `board.processor.cores0.core.ipc` |

## Register File & Rename

| McPAT XML Field | gem5 Classic | gem5 v25 stdlib |
|---|---|---|
| `int_regfile_reads` | `system.cpu0.int_regfile_reads` | `board.processor.cores0.core.executeStats0.numIntRegReads` |
| `int_regfile_writes` | `system.cpu0.int_regfile_writes` | `board.processor.cores0.core.executeStats0.numIntRegWrites` |
| `float_regfile_reads` | `system.cpu0.fp_regfile_reads` | `board.processor.cores0.core.executeStats0.numVecRegReads` |
| `float_regfile_writes` | `system.cpu0.fp_regfile_writes` | `board.processor.cores0.core.executeStats0.numFpRegWrites` |
| `rename_reads` | `system.cpu0.rename.int_rename_lookups` | `board.processor.cores0.core.rename.intLookups` |
| `fp_rename_reads` | `system.cpu0.rename.fp_rename_lookups` | `board.processor.cores0.core.rename.vecLookups` |
| `ROB_reads` | `system.cpu0.rob.rob_reads` | `board.processor.cores0.core.rob.reads` |
| `ROB_writes` | `system.cpu0.rob.rob_writes` | `board.processor.cores0.core.rob.writes` |

## Instruction Queue

| McPAT XML Field | gem5 Classic | gem5 v25 stdlib |
|---|---|---|
| `inst_window_reads` | `system.cpu0.iq.int_inst_queue_reads` | `board.processor.cores0.core.intInstQueueReads` |
| `inst_window_writes` | `system.cpu0.iq.int_inst_queue_writes` | `board.processor.cores0.core.intInstQueueWrites` |
| `inst_window_wakeup_accesses` | `system.cpu0.iq.int_inst_queue_wakeup_accesses` | `board.processor.cores0.core.intInstQueueWakeupAccesses` |
| `fp_inst_window_reads` | `system.cpu0.iq.fp_inst_queue_reads` | `board.processor.cores0.core.fpInstQueueReads` |
| `fp_inst_window_writes` | `system.cpu0.iq.fp_inst_queue_writes` | `board.processor.cores0.core.fpInstQueueWrites` |
| `fp_inst_window_wakeup_accesses` | `system.cpu0.iq.fp_inst_queue_wakeup_accesses` | `board.processor.cores0.core.fpInstQueueWakeupAccesses` |

## Functional Units

| McPAT XML Field | gem5 Classic | gem5 v25 stdlib |
|---|---|---|
| `ialu_accesses` | `system.cpu0.num_int_alu_accesses` | `board.processor.cores0.core.intAluAccesses` |
| `fpu_accesses` | `system.cpu0.num_fp_alu_accesses` | `board.processor.cores0.core.fpAluAccesses` |
| `function_calls` | `system.cpu0.commit.function_calls` | `board.processor.cores0.core.commit.functionCalls` |

## Caches

| McPAT XML Field | gem5 Classic | gem5 v25 stdlib |
|---|---|---|
| `icache.read_accesses` | `system.cpu0.icache.ReadReq_accesses::total` | `board.cache_hierarchy.l1i-cache-0.ReadReq.accesses::total` |
| `icache.read_misses` | `system.cpu0.icache.ReadReq_misses::total` | `board.cache_hierarchy.l1i-cache-0.ReadReq.misses::total` |
| `dcache.read_accesses` | `system.cpu0.dcache.ReadReq_accesses::total` | `board.cache_hierarchy.l1d-cache-0.ReadReq.accesses::total` |
| `dcache.write_accesses` | `system.cpu0.dcache.WriteReq_accesses::total` | `board.cache_hierarchy.l1d-cache-0.WriteReq.accesses::total` |
| `dcache.read_misses` | `system.cpu0.dcache.ReadReq_misses::total` | `board.cache_hierarchy.l1d-cache-0.ReadReq.misses::total` |
| `dcache.write_misses` | `system.cpu0.dcache.WriteReq_misses::total` | `board.cache_hierarchy.l1d-cache-0.WriteReq.misses::total` |

## Branch Target Buffer

| McPAT XML Field | gem5 Classic | gem5 v25 stdlib |
|---|---|---|
| `BTB.read_accesses` | `system.cpu0.branchPred.BTBLookups` | `board.processor.cores0.core.branchPred.BTBLookups` |
| `BTB.write_accesses` | `system.cpu0.branchPred.BTBHits` | `board.processor.cores0.core.branchPred.BTBUpdates` |

## Memory Controller

| McPAT XML Field | gem5 Classic | gem5 v25 stdlib |
|---|---|---|
| `mc.memory_reads` | `system.mem_ctrls.readReqs` | `board.memory.mem_ctrl.readReqs` |
| `mc.memory_writes` | `system.mem_ctrls.writeReqs` | `board.memory.mem_ctrl.writeReqs` |

## Notes

- Replace `cores0` with `coresN` for multi-core indexing (N = 0, 1, 2, 3)
- Replace `l1d-cache-0` with `l1d-cache-N` similarly
- The translation is implemented in `parser/writeStatValue_v25_fix.py`
