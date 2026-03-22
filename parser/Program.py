from writeStatValue_v25_fix import build_core_mappings_v25, apply_resolved_to_xml
import xml.etree.cElementTree as ET
import sys
import json
import copy
import re # For regular expressions

config = {}
stats = {}
tree = None
noCores = 0
mapping = {}
l3_exists = False
l3_key = None

def main():
    # Use this command to run the script
    # python3 Program.py <statFileName> <configFileName> <mcpat-templateFile>

    command = "python3 Program.py stats.txt config.json mcpat-template.xml"

    # Must be 3 files in the input
    if len(sys.argv) != 4:
        print(f"Input format is incorrect. Use this format: {command}")
        sys.exit(1)

    # Checking file types
    if not (sys.argv[1].endswith(".txt") and sys.argv[2].endswith(".json") and sys.argv[3].endswith(".xml")):
        print(f"ERROR: Please use appropriate file: {command}")
        sys.exit(1)

    # tree contains xml-template file, mapping dict for strings from xml to config/stat,
    # stats dict contains all the values from the stats file
    global tree, mapping, stats

    # parsing xml file into tree
    try:
        tree = ET.parse(sys.argv[3])
    except (IOError, FileNotFoundError):
        print("******ERROR: Template file not found******")
        sys.exit(1)

    mapping = {}
    stats = {}
    l3_exists = False  # ADD THIS
    l3_key = None  # ADD THIS

    # First we will count no. of cores from config file
    countCores(sys.argv[2])
    # We will change xml format according to no. of cores
    changeXML()
    # Verify xml structure
    verify_xml_structure()



    # read every value from stat file
    readStatsFile(sys.argv[1])
    # read value from config file then write into tree
    readWriteConfigValue(sys.argv[2])
    # write stat value to tree
    writeStatValue(sys.argv[3])

    # handle spaces with specific format in tree component
    indent(tree.getroot())

    # print tree into xml file
    out_file = sys.argv[2].split("/")[-1][:-5] + ".xml"
    tree.write(out_file, encoding="utf-8", xml_declaration=True)
    print(f"Output written to: {out_file}")

# Goran: completed getting number of cores from config file
def countCores(configFile):
    try:
        file = open(configFile)
    except IOError:
        print("******ERROR: File not found or can't open config file******")
        sys.exit(1)

    configfile = json.load(file)

    # Global variable we will use this elsewhere in the code
    global noCores

    # Try NEW gem5 format first (board.processor.cores)
    if "board" in configfile:
        if "processor" in configfile["board"]:
            if "cores" in configfile["board"]["processor"]:
                noCores = len(configfile["board"]["processor"]["cores"])
                print(f"Detected {noCores} cores (new gem5 format)")
                file.close()
                return

    # Fallback to OLD gem5 format (system.cpu)
    if "system" in configfile:
        if "cpu" in configfile["system"]:
            cpus = configfile["system"]["cpu"]
            # Handle both list and single CPU
            if isinstance(cpus, list):
                noCores = len(cpus)
            else:
                noCores = 1
            print(f"Detected {noCores} cores (old gem5 format)")
            file.close()
            return

    # If neither format found
    print("******ERROR: Cannot determine number of cores from config file******")
    print("Expected either 'board.processor.cores' or 'system.cpu' in config")
    sys.exit(1)

    file.close()

# Goran: completed changeXML to support multiple cores
def changeXML():
    """
    Modifies McPAT template XML to support multiple cores.
    Automatically detects component structure and replicates cores.
    """
    root = tree.getroot()
    systemElement = root.find("./component")

    if systemElement is None:
        print("******ERROR: Cannot find system component in template XML******")
        sys.exit(1)

    # ==========================================
    # STEP 1: Extract and categorize components
    # ==========================================
    components = list(systemElement.findall("./component"))

    if len(components) == 0:
        print("******ERROR: No components found in template XML******")
        sys.exit(1)

    # Categorize components
    core_components = []
    l2_components = []
    shared_components = []

    for comp in components:
        comp_id = comp.get('id', '')
        comp_name = comp.get('name', '')

        # Identify component type by name/id
        if 'core' in comp_name.lower() or 'core' in comp_id.lower():
            core_components.append(comp)
        elif 'l2' in comp_name.lower() and 'directory' not in comp_name.lower():
            l2_components.append(comp)
        else:
            shared_components.append(comp)

    print(f"Detected components:")
    print(f"  - Cores: {len(core_components)}")
    print(f"  - L2 caches: {len(l2_components)}")
    print(f"  - Shared: {len(shared_components)}")

    # Use first core as template
    if len(core_components) == 0:
        print("******ERROR: No core component found in template******")
        sys.exit(1)

    core_template = core_components[0]

    # Use first L2 as template (if exists)
    l2_template = l2_components[0] if len(l2_components) > 0 else None

    # ==========================================
    # STEP 2: Clear all components from system
    # ==========================================
    for comp in components:
        systemElement.remove(comp)

    print(f"\nGenerating XML for {noCores} cores...")

    # ==========================================
    # STEP 3: Create and add core replicas
    # ==========================================
    for core_num in range(noCores):
        # Deep copy the core template
        new_core = copy.deepcopy(core_template)

        # Update core ID and name
        new_core.set('id', f"system.core{core_num}")
        new_core.set('name', f"core{core_num}")

        # Update ALL nested component IDs
        update_component_ids(new_core, core_num)

        # Add to system
        systemElement.append(new_core)
        print(f"  ✓ Added core{core_num}")

    # ==========================================
    # STEP 4: Add shared components
    # ==========================================
    for shared_comp in shared_components:
        systemElement.append(shared_comp)
        comp_name = shared_comp.get('name', 'unknown')
        print(f"  ✓ Added shared component: {comp_name}")

    # ==========================================
    # STEP 5: Create and add L2 cache replicas (if private L2)
    # ==========================================
    if l2_template is not None:
        for core_num in range(noCores):
            new_l2 = copy.deepcopy(l2_template)

            # Update L2 ID and name
            new_l2.set('id', f"system.L2{core_num}")
            new_l2.set('name', f"L2{core_num}")

            # Update nested component IDs for L2
            for subcomp in new_l2.iter('component'):
                old_id = subcomp.get('id', '')
                if old_id:
                    # Replace L2 index in ID
                    new_id = old_id.replace('L20', f'L2{core_num}')
                    new_id = new_id.replace('L2.', f'L2{core_num}.')
                    subcomp.set('id', new_id)

            systemElement.append(new_l2)
            print(f"  ✓ Added L2{core_num}")

    print(f"\n✓ XML structure updated successfully")
def update_component_ids(component, core_num):
    """
    Recursively updates all component IDs to reflect the new core number.

    Args:
        component: XML element to update
        core_num: New core number (0, 1, 2, ...)
    """
    for subcomp in component.iter('component'):
        old_id = subcomp.get('id', '')

        if not old_id:
            continue

        # Split ID into parts
        id_parts = old_id.split('.')

        # Find and update core identifier
        for i, part in enumerate(id_parts):
            if 'core' in part.lower():
                # Replace with new core number
                id_parts[i] = f"core{core_num}"
                break

        # Rebuild ID
        new_id = '.'.join(id_parts)
        subcomp.set('id', new_id)
def verify_xml_structure():
    """
    Verifies the modified XML has correct structure.
    Call this after changeXML() to validate.
    """
    root = tree.getroot()
    systemElement = root.find("./component")

    if systemElement is None:
        print("⚠ WARNING: System component not found")
        return False

    components = systemElement.findall("./component")
    core_count = sum(1 for c in components if 'core' in c.get('name', '').lower())

    print(f"\nXML Verification:")
    print(f"  Total components: {len(components)}")
    print(f"  Core components: {core_count}")
    print(f"  Expected cores: {noCores}")

    if core_count == noCores:
        print("  ✓ Core count matches!")
        return True
    else:
        print(f"  ✗ Mismatch! Expected {noCores}, found {core_count}")
        return False
# end of verify_xml_structure


def readStatsFile(statFile):
    """
    Read gem5 stats.txt file and extract statistics

    Works with both old and new gem5 stat file formats
    Stores values in global 'stats' dictionary
    """
    print(f"Reading Stat File: {statFile}")

    try:
        File = open(statFile)
    except IOError:
        print("******ERROR: File not found or can't open stat file******")
        sys.exit(1)

    # Ignoring lines starting with "---" or "------"
    ignore_patterns = ["---", "------"]
    count = 2

    # For each line in stat file
    for line in File:
        # Skip lines with ignore patterns
        if any(pattern in line for pattern in ignore_patterns):
            continue

        # Skip empty lines
        if not line.strip():
            continue

        # Split line by whitespace
        lineArray = line.split()

        # Need at least 2 elements (name and value)
        if len(lineArray) < 2:
            continue

        Name = lineArray[0]  # First element is the stat name
        val = None

        # Try to find numeric value in the line
        # Usually it's the second element, but we search all elements
        for e in lineArray[1:]:  # Skip first element (name)
            # Remove any trailing characters like commas
            e = e.rstrip(',')

            try:
                val = int(e)  # Try as integer
                break
            except ValueError:
                try:
                    val = float(e)  # Try as float
                    break
                except ValueError:
                    continue

        # Only store if we found a valid value
        if val is not None:
            stats[Name] = val
            count += 1

    File.close()
    print(f"Done - Read {count} statistics")


# Example usage:
# stats = {}
# readStatsFile("m5out/stats.txt")
# print(stats["system.cpu0.commit.loads"])


def readWriteConfigValue(configFile):
    global config, noCores, mapping, stats, tree, l3_exists, l3_key  # ADD l3_exists, l3_key
    print(f"Reading config File: {configFile}")

    try:
        file = open(configFile)
    except IOError:
        print("******ERROR: File not found or can't open config file******")
        sys.exit(1)

    config = json.load(file)
    file.close()

    # ============================================================
    # DETECT NUMBER OF CORES (NEW FORMAT)
    # ============================================================
    # NEW format: board.processor.cores is an array
    if "board" in config and "processor" in config["board"]:
        noCores = len(config["board"]["processor"]["cores"])
    else:
        print("******ERROR: This parser only supports NEW gem5 config format (board-based)******")
        print("Expected structure: config['board']['processor']['cores']")
        sys.exit(1)

    print(f"Detected {noCores} cores in NEW config format")

    # This is parent-child mapping we need parent of any child of xml-tree we will use this
    parent_map = {c: p for p in tree.getroot().iter() for c in p}

    root = tree.getroot()

    # After getting value from config file if we have operation on the value that will goes here
    params = {}

    # This array contains default values that are not in config file but we are setting manually from this code
    defaultChangedConfigValue = {}

    defaultChangedConfigValue["system.number_of_cores"] = str(noCores)
    defaultChangedConfigValue["system.number_of_L2s"] = "0"
    defaultChangedConfigValue["system.Private_L2"] = "0"
    defaultChangedConfigValue["system.homogeneous_cores"] = "0"
    defaultChangedConfigValue["system.homogeneous_L2s"] = "0"
    defaultChangedConfigValue["system.number_of_L3s"] = "0"
    defaultChangedConfigValue["system.mc.number_mcs"] = "1"
    defaultChangedConfigValue["system.number_of_NoCs"] = "0"
    defaultChangedConfigValue["system.number_of_L1Directories"] = "0"
    defaultChangedConfigValue["system.number_of_L2Directories"] = "0"

    # ============================================================
    # PER-CORE DEFAULT VALUES
    # ============================================================
    for no in range(0, noCores):
        # I-Cache defaults
        defaultChangedConfigValue["system.cpu" + str(no) + ".icache.cache_policy"] = "1"
        defaultChangedConfigValue["system.cpu" + str(no) + ".icache.bank"] = "1"

        # Calculate I-cache throughput from stats
        # NEW format: board.cache_hierarchy.l1i-cache-0.overallAccesses::total
        try:
            icache_accesses = stats.get(
                f"board.cache_hierarchy.l1i-cache-{no}.overallAccesses::total",
                stats.get(f"board.cache_hierarchy.l1i-cache-{no}.demandAccesses::total", 0)
            )
            sim_ticks = stats.get("simTicks", stats.get("sim_ticks", 1))

            if icache_accesses and sim_ticks:
                defaultChangedConfigValue["system.cpu" + str(no) + ".icache.throughput"] = float(
                    icache_accesses) / float(sim_ticks)
            else:
                defaultChangedConfigValue["system.cpu" + str(no) + ".icache.throughput"] = 0
        except (KeyError, TypeError, ZeroDivisionError):
            defaultChangedConfigValue["system.cpu" + str(no) + ".icache.throughput"] = 0

        # D-Cache defaults
        defaultChangedConfigValue["system.cpu" + str(no) + ".dcache.cache_policy"] = "1"
        defaultChangedConfigValue["system.cpu" + str(no) + ".dcache.bank"] = "1"

        # Calculate D-cache throughput from stats
        # NEW format: board.cache_hierarchy.l1d-cache-0.overallAccesses::total
        try:
            dcache_accesses = stats.get(
                f"board.cache_hierarchy.l1d-cache-{no}.overallAccesses::total",
                stats.get(f"board.cache_hierarchy.l1d-cache-{no}.demandAccesses::total", 0)
            )
            sim_ticks = stats.get("simTicks", stats.get("sim_ticks", 1))

            if dcache_accesses and sim_ticks:
                defaultChangedConfigValue["system.cpu" + str(no) + ".dcache.throughput"] = float(
                    dcache_accesses) / float(sim_ticks)
            else:
                defaultChangedConfigValue["system.cpu" + str(no) + ".dcache.throughput"] = 0
        except (KeyError, TypeError, ZeroDivisionError):
            defaultChangedConfigValue["system.cpu" + str(no) + ".dcache.throughput"] = 0

        # Branch Predictor defaults
        defaultChangedConfigValue["system.cpu" + str(no) + ".branchPred.bank"] = "1"

        # Calculate branch predictor throughput from stats
        # Branch predictor stats are likely still at processor.cores level
        try:
            bp_lookups = stats.get(
                f"board.processor.cores{no}.core.branchPred.lookups",
                0
            )
            sim_ticks = stats.get("simTicks", stats.get("sim_ticks", 1))

            if bp_lookups and sim_ticks:
                defaultChangedConfigValue["system.cpu" + str(no) + ".branchPred.throughput"] = float(
                    bp_lookups) / float(sim_ticks)
            else:
                defaultChangedConfigValue["system.cpu" + str(no) + ".branchPred.throughput"] = 0
        except (KeyError, TypeError, ZeroDivisionError):
            defaultChangedConfigValue["system.cpu" + str(no) + ".branchPred.throughput"] = 0

        # L2 Cache defaults
        defaultChangedConfigValue["system.cpu" + str(no) + ".l2cache.cache_policy"] = "1"
        defaultChangedConfigValue["system.cpu" + str(no) + ".l2cache.bank"] = "1"

        # Calculate L2 cache throughput from stats
        # NEW format: board.cache_hierarchy.l2-cache-0.overallAccesses::total
        try:
            l2cache_accesses = stats.get(
                f"board.cache_hierarchy.l2-cache-{no}.overallAccesses::total",
                stats.get(f"board.cache_hierarchy.l2-cache-{no}.demandAccesses::total", 0)
            )
            sim_ticks = stats.get("simTicks", stats.get("sim_ticks", 1))

            if l2cache_accesses and sim_ticks:
                defaultChangedConfigValue["system.cpu" + str(no) + ".l2cache.throughput"] = float(
                    l2cache_accesses) / float(sim_ticks)
            else:
                defaultChangedConfigValue["system.cpu" + str(no) + ".l2cache.throughput"] = 0
        except (KeyError, TypeError, ZeroDivisionError):
            defaultChangedConfigValue["system.cpu" + str(no) + ".l2cache.throughput"] = 0

    # ============================================================
    # L3 CACHE DEFAULTS (if exists)
    # ============================================================
    # In NEW format: board.cache_hierarchy might have L3
    # Check if L3 exists before setting defaults

    # Try to detect if L3 cache exists in NEW format
    l3_exists = False
    l3_key = None
    if "board" in config and "cache_hierarchy" in config["board"]:
        cache_hierarchy = config["board"]["cache_hierarchy"]
        # L3 might be named: "l3", "l3-cache", "l3-cache-0", etc.
        for key in cache_hierarchy.keys():
            if "l3" in key.lower():
                l3_exists = True
                l3_key = key
                break

    if l3_exists:
        print(f"L3 cache detected in config: {l3_key}")
        defaultChangedConfigValue["system.l3.cache_policy"] = "1"
        defaultChangedConfigValue["system.l3.bank"] = "1"

        # Calculate L3 throughput from stats if available
        # NEW format: board.cache_hierarchy.l3.overallAccesses::total (or similar)
        try:
            l3_accesses = stats.get(
                f"board.cache_hierarchy.{l3_key}.overallAccesses::total",
                stats.get(f"board.cache_hierarchy.{l3_key}.demandAccesses::total", 0)
            )
            sim_ticks = stats.get("simTicks", stats.get("sim_ticks", 1))

            if l3_accesses and sim_ticks:
                defaultChangedConfigValue["system.l3.throughput"] = float(l3_accesses) / float(sim_ticks)
            else:
                defaultChangedConfigValue["system.l3.throughput"] = 0
        except (KeyError, TypeError, ZeroDivisionError):
            defaultChangedConfigValue["system.l3.throughput"] = 0
    else:
        print("No L3 cache detected in config")
        # Set defaults even if L3 doesn't exist (McPAT XML might still need them)
        defaultChangedConfigValue["system.l3.cache_policy"] = "1"
        defaultChangedConfigValue["system.l3.bank"] = "1"
        defaultChangedConfigValue["system.l3.throughput"] = 0

    # ============================================================
    # ARCHITECTURE TYPE & EMBEDDED FLAG
    # ============================================================
    # Detect architecture type from NEW format
    X86 = getConfValue("system.cpu0.isa.type")

    if X86 == -1:
        # Try alternative path for ISA array
        X86 = getConfValue("system.cpu0.isa.0.type")

    if X86 == -1:
        print("WARNING: Could not detect ISA type, defaulting to Arm")
        X86 = "ArmISA"

    archType = X86

    # Set INT_EXE and FP_EXE for pipeline depth calculation
    if archType[:3] == "X86":
        INT_EXE = 2
        FP_EXE = 8
    elif archType[:3] == "Arm":
        INT_EXE = 3
        FP_EXE = 7
    else:
        INT_EXE = 3
        FP_EXE = 6

    # Convert to McPAT format (0 = Arm, 1 = x86)
    if X86[:3] == "Arm":
        X86 = "0"
    else:
        X86 = "1"

    # Set x86 flag for each core
    for no in range(0, noCores):
        defaultChangedConfigValue["system.core" + str(no) + ".x86"] = X86

    # Set Embedded flag based on architecture
    if X86 == "0":
        defaultChangedConfigValue["system.Embedded"] = "1"
    else:
        defaultChangedConfigValue["system.Embedded"] = "0"

    # ============================================================
    # CALCULATE PIPELINE DEPTH FOR EACH CORE
    # ============================================================
    for no in range(0, noCores):
        # Get pipeline stage delays (getConfValue auto-translates NEW format paths)
        fetchToDecodeDelay = getConfValue("system.cpu" + str(no) + ".fetchToDecodeDelay")
        decodeToRenameDelay = getConfValue("system.cpu" + str(no) + ".decodeToRenameDelay")
        renameToIEWDelay = getConfValue("system.cpu" + str(no) + ".renameToIEWDelay")
        iewToCommitDelay = getConfValue("system.cpu" + str(no) + ".iewToCommitDelay")

        # Handle missing values (use default of 1 if not found)
        if fetchToDecodeDelay == -1: fetchToDecodeDelay = 1
        if decodeToRenameDelay == -1: decodeToRenameDelay = 1
        if renameToIEWDelay == -1: renameToIEWDelay = 1
        if iewToCommitDelay == -1: iewToCommitDelay = 1

        base = fetchToDecodeDelay + decodeToRenameDelay + renameToIEWDelay + iewToCommitDelay

        # Get commit delays
        cToDecode = getConfValue("system.cpu" + str(no) + ".commitToDecodeDelay")
        cToFetch = getConfValue("system.cpu" + str(no) + ".commitToFetchDelay")
        cToIew = getConfValue("system.cpu" + str(no) + ".commitToIEWDelay")
        cToRename = getConfValue("system.cpu" + str(no) + ".commitToRenameDelay")

        # Handle missing values
        if cToDecode == -1: cToDecode = 1
        if cToFetch == -1: cToFetch = 1
        if cToIew == -1: cToIew = 1
        if cToRename == -1: cToRename = 1

        maxBase = max(cToDecode, cToFetch, cToIew, cToRename)

        # Calculate pipeline depths (INT and FP)
        pipeline_depthValue = str(INT_EXE + base + maxBase) + "," + str(FP_EXE + base + maxBase)
        defaultChangedConfigValue["system.core" + str(no) + ".pipeline_depth"] = pipeline_depthValue

        print(f"Core {no} pipeline depth: {pipeline_depthValue}")

    # ============================================================
    # MAPPING FROM MCPAT XML TO CONFIG FILE PATHS
    # ============================================================
    # Here we have mapping from template-xml file to name from config or stat file
    mapping = {}

    # System-level mappings
    mapping["system.number_of_cores"] = "system.number_of_cores"
    mapping["system.number_of_L1Directories"] = "system.number_of_L1Directories"
    mapping["system.number_of_L2Directories"] = "system.number_of_L2Directories"
    mapping["system.number_of_L2s"] = "system.number_of_cores"
    mapping["system.Private_L2"] = "system.Private_L2"
    mapping["system.number_of_L3s"] = "system.number_of_L3s"
    mapping["system.number_of_NoCs"] = "system.number_of_NoCs"
    mapping["system.homogeneous_cores"] = "system.homogeneous_cores"
    mapping["system.homogeneous_L2s"] = "system.homogeneous_L2s"
    mapping["system.homogeneous_L1Directories"] = "default"
    mapping["system.homogeneous_L2Directories"] = "default"
    mapping["system.homogeneous_L3s"] = "default"
    mapping["system.homogeneous_ccs"] = "default"
    mapping["system.homogeneous_NoCs"] = "default"
    mapping["system.core_tech_node"] = "default"
    mapping["system.target_core_clockrate"] = "system.cpu_clk_domain.clock"
    mapping["system.temperature"] = "default"
    mapping["system.number_cache_levels"] = "default"
    mapping["system.interconnect_projection_type"] = "default"
    mapping["system.device_type"] = "default"
    mapping["system.longer_channel_device"] = "default"
    mapping["system.Embedded"] = "system.Embedded"
    mapping["system.power_gating"] = "default"
    mapping["system.opt_clockrate"] = "default"
    mapping["system.machine_bits"] = "default"
    mapping["system.virtual_address_width"] = "default"
    mapping["system.physical_address_width"] = "default"
    mapping["system.virtual_memory_page_size"] = "default"

    #For multi-core we are using loop for mapping
    # ============================================================
    # PER-CORE MAPPINGS
    # ============================================================
    # For multi-core we are using loop for mapping
    for no in range(0, noCores):
        # Core-level parameters
        mapping["system.core" + str(no) + ".clock_rate"] = "system.cpu_clk_domain.clock"
        mapping["system.core" + str(no) + ".vdd"] = "default"
        mapping["system.core" + str(no) + ".power_gating_vcc"] = "default"
        mapping["system.core" + str(no) + ".opt_local"] = "default"
        mapping["system.core" + str(no) + ".instruction_length"] = "default"
        mapping["system.core" + str(no) + ".opcode_width"] = "default"
        mapping["system.core" + str(no) + ".x86"] = "system.core" + str(no) + ".x86"
        mapping["system.core" + str(no) + ".micro_opcode_width"] = "default"
        mapping["system.core" + str(no) + ".machine_type"] = "default"

        # CPU parameters (getConfValue will translate to NEW format)
        mapping["system.core" + str(no) + ".number_hardware_threads"] = "system.cpu" + str(no) + ".numThreads"
        mapping["system.core" + str(no) + ".fetch_width"] = "system.cpu" + str(no) + ".fetchWidth"
        mapping["system.core" + str(no) + ".number_instruction_fetch_ports"] = "default"
        mapping["system.core" + str(no) + ".decode_width"] = "system.cpu" + str(no) + ".decodeWidth"
        mapping["system.core" + str(no) + ".issue_width"] = "system.cpu" + str(no) + ".issueWidth"
        mapping["system.core" + str(no) + ".peak_issue_width"] = "default"
        mapping["system.core" + str(no) + ".commit_width"] = "system.cpu" + str(no) + ".commitWidth"
        mapping["system.core" + str(no) + ".fp_issue_width"] = "default"
        mapping["system.core" + str(no) + ".prediction_width"] = "default"
        mapping["system.core" + str(no) + ".pipelines_per_core"] = "default"
        mapping["system.core" + str(no) + ".pipeline_depth"] = "system.core" + str(no) + ".pipeline_depth"
        mapping["system.core" + str(no) + ".ALU_per_core"] = "default"
        mapping["system.core" + str(no) + ".MUL_per_core"] = "default"
        mapping["system.core" + str(no) + ".FPU_per_core"] = "default"
        mapping["system.core" + str(no) + ".instruction_buffer_size"] = "system.cpu" + str(no) + ".fetchBufferSize"
        mapping["system.core" + str(no) + ".decoded_stream_buffer_size"] = "default"
        mapping["system.core" + str(no) + ".instruction_window_scheme"] = "default"

        # IQ Entries (divide by 2 for McPAT)
        mapping["system.core" + str(no) + ".instruction_window_size"] = "system.cpu" + str(no) + ".numIQEntries"
        iq_value = getConfValue("system.cpu" + str(no) + ".numIQEntries")
        if iq_value != -1:
            params["system.cpu" + str(no) + ".numIQEntries"] = iq_value / 2

        mapping["system.core" + str(no) + ".fp_instruction_window_size"] = "system.cpu" + str(no) + ".numIQEntries"
        # Note: params already set above, so same value used

        # ROB and Register Files
        mapping["system.core" + str(no) + ".ROB_size"] = "system.cpu" + str(no) + ".numROBEntries"
        mapping["system.core" + str(no) + ".archi_Regs_IRF_size"] = "default"
        mapping["system.core" + str(no) + ".archi_Regs_FRF_size"] = "default"
        mapping["system.core" + str(no) + ".phy_Regs_IRF_size"] = "system.cpu" + str(no) + ".numPhysIntRegs"
        mapping["system.core" + str(no) + ".phy_Regs_FRF_size"] = "system.cpu" + str(no) + ".numPhysFloatRegs"
        mapping["system.core" + str(no) + ".rename_scheme"] = "default"
        mapping["system.core" + str(no) + ".checkpoint_depth"] = "default"
        mapping["system.core" + str(no) + ".register_windows_size"] = "default"

        # Load/Store Unit
        mapping["system.core" + str(no) + ".LSU_order"] = "default"
        mapping["system.core" + str(no) + ".store_buffer_size"] = "system.cpu" + str(no) + ".SQEntries"
        mapping["system.core" + str(no) + ".load_buffer_size"] = "system.cpu" + str(no) + ".LQEntries"
        mapping["system.core" + str(no) + ".memory_ports"] = "default"

        # Branch Predictor
        mapping["system.core" + str(no) + ".RAS_size"] = "system.cpu" + str(no) + ".branchPred.RASSize"
        mapping["system.core" + str(no) + ".number_of_BPT"] = "default"
        mapping["system.core" + str(no) + ".predictor.local_predictor_size"] = "system.cpu" + str(
            no) + ".branchPred.localPredictorSize"
        mapping["system.core" + str(no) + ".predictor.local_predictor_entries"] = "system.cpu" + str(
            no) + ".branchPred.localHistoryTableSize"
        mapping["system.core" + str(no) + ".predictor.global_predictor_entries"] = "system.cpu" + str(
            no) + ".branchPred.globalPredictorSize"
        mapping["system.core" + str(no) + ".predictor.global_predictor_bits"] = "system.cpu" + str(
            no) + ".branchPred.globalCtrBits"
        mapping["system.core" + str(no) + ".predictor.chooser_predictor_entries"] = "system.cpu" + str(
            no) + ".branchPred.choicePredictorSize"
        mapping["system.core" + str(no) + ".predictor.chooser_predictor_bits"] = "system.cpu" + str(
            no) + ".branchPred.choiceCtrBits"

        # TLB
        mapping["system.core" + str(no) + ".itlb.number_entries"] = "system.cpu" + str(no) + ".itb.size"
        mapping["system.core" + str(no) + ".dtlb.number_entries"] = "system.cpu" + str(no) + ".dtb.size"

        # I-Cache Configuration (8 comma-separated values)
        mapping["system.core" + str(no) + ".icache.icache_config"] = (
                "system.cpu" + str(no) + ".icache.size,"
                                         "system.cpu" + str(no) + ".icache.tags.block_size,"
                                                                  "system.cpu" + str(no) + ".icache.assoc,"
                                                                                           "system.cpu" + str(
            no) + ".icache.bank,"
                  "system.cpu" + str(no) + ".icache.throughput,"
                                           "system.cpu" + str(no) + ".icache.response_latency,"
                                                                    "system.cpu" + str(no) + ".icache.tags.block_size,"
                                                                                             "system.cpu" + str(
            no) + ".icache.cache_policy"
        )

        # I-Cache Buffer Sizes (4 comma-separated values - all same)
        mapping["system.core" + str(no) + ".icache.buffer_sizes"] = (
                "system.cpu" + str(no) + ".icache.mshrs,"
                                         "system.cpu" + str(no) + ".icache.mshrs,"
                                                                  "system.cpu" + str(no) + ".icache.mshrs,"
                                                                                           "system.cpu" + str(
            no) + ".icache.mshrs"
        )

        # D-Cache Configuration (8 comma-separated values)
        mapping["system.core" + str(no) + ".dcache.dcache_config"] = (
                "system.cpu" + str(no) + ".dcache.size,"
                                         "system.cpu" + str(no) + ".dcache.tags.block_size,"
                                                                  "system.cpu" + str(no) + ".dcache.assoc,"
                                                                                           "system.cpu" + str(
            no) + ".dcache.bank,"
                  "system.cpu" + str(no) + ".dcache.throughput,"
                                           "system.cpu" + str(no) + ".dcache.response_latency,"
                                                                    "system.cpu" + str(no) + ".dcache.tags.block_size,"
                                                                                             "system.cpu" + str(
            no) + ".dcache.cache_policy"
        )

        # D-Cache Buffer Sizes (4 comma-separated values - all same)
        mapping["system.core" + str(no) + ".dcache.buffer_sizes"] = (
                "system.cpu" + str(no) + ".dcache.mshrs,"
                                         "system.cpu" + str(no) + ".dcache.mshrs,"
                                                                  "system.cpu" + str(no) + ".dcache.mshrs,"
                                                                                           "system.cpu" + str(
            no) + ".dcache.mshrs"
        )

        # BTB (Branch Target Buffer) Configuration
        mapping["system.core" + str(no) + ".number_of_BTB"] = "default"
        mapping["system.core" + str(no) + ".BTB.BTB_config"] = (
                "system.cpu" + str(no) + ".branchPred.BTBEntries,"
                                         "system.cpu" + str(no) + ".branchPred.BTBTagSize,"
                                                                  "system.cpu" + str(no) + ".branchPred.indirectWays,"
                                                                                           "system.cpu" + str(
            no) + ".branchPred.bank,"
                  "system.cpu" + str(no) + ".branchPred.throughput,"
                                           "system.cpu" + str(no) + ".icache.response_latency"
        )
    #for k, v in mapping.items():
        #print(f"{k} => {v}")

    # ============================================================
    # CACHE DIRECTORY MAPPINGS (for coherence protocols)
    # ============================================================
    # If more than 1 directory exists, change the range value
    # Most simple configs don't have directories, so these use defaults

    for no in range(0, 1):
        # L1 Directory mappings
        mapping["system.L1Directory" + str(no) + ".Directory_type"] = "default"
        mapping["system.L1Directory" + str(no) + ".Dir_config"] = "default"
        mapping["system.L1Directory" + str(no) + ".buffer_sizes"] = "default"
        mapping["system.L1Directory" + str(no) + ".clockrate"] = "system.cpu_clk_domain.clock"
        mapping["system.L1Directory" + str(no) + ".ports"] = "default"
        mapping["system.L1Directory" + str(no) + ".device_type"] = "default"
        mapping["system.L1Directory" + str(no) + ".vdd"] = "default"
        mapping["system.L1Directory" + str(no) + ".power_gating_vcc"] = "default"

        # L2 Directory mappings
        mapping["system.L2Directory" + str(no) + ".Directory_type"] = "default"
        mapping["system.L2Directory" + str(no) + ".Dir_config"] = "default"
        mapping["system.L2Directory" + str(no) + ".buffer_sizes"] = "default"
        mapping["system.L2Directory" + str(no) + ".clockrate"] = "system.cpu_clk_domain.clock"
        mapping["system.L2Directory" + str(no) + ".ports"] = "default"
        mapping["system.L2Directory" + str(no) + ".device_type"] = "default"
        mapping["system.L2Directory" + str(no) + ".vdd"] = "default"
        mapping["system.L2Directory" + str(no) + ".power_gating_vcc"] = "default"

    # ============================================================
    # L2 CACHE MAPPINGS (per-core L2 caches)
    # ============================================================
    for no in range(0, noCores):
        # L2 Cache Configuration (8 comma-separated values)
        mapping["system.L2" + str(no) + ".L2_config"] = (
                "system.cpu" + str(no) + ".l2cache.size,"
                                         "system.cpu" + str(no) + ".l2cache.tags.block_size,"
                                                                  "system.cpu" + str(no) + ".l2cache.assoc,"
                                                                                           "system.cpu" + str(
            no) + ".l2cache.bank,"
                  "system.cpu" + str(no) + ".l2cache.throughput,"
                                           "system.cpu" + str(no) + ".l2cache.response_latency,"
                                                                    "system.cpu" + str(no) + ".l2cache.tags.block_size,"
                                                                                             "system.cpu" + str(
            no) + ".l2cache.cache_policy"
        )

        # L2 Cache Buffer Sizes (4 comma-separated values - all same)
        mapping["system.L2" + str(no) + ".buffer_sizes"] = (
                "system.cpu" + str(no) + ".l2cache.mshrs,"
                                         "system.cpu" + str(no) + ".l2cache.mshrs,"
                                                                  "system.cpu" + str(no) + ".l2cache.mshrs,"
                                                                                           "system.cpu" + str(
            no) + ".l2cache.mshrs"
        )

        # L2 Cache Other Parameters
        mapping["system.L2" + str(no) + ".clockrate"] = "system.cpu_clk_domain.clock"
        mapping["system.L2" + str(no) + ".ports"] = "default"
        mapping["system.L2" + str(no) + ".device_type"] = "default"
        mapping["system.L2" + str(no) + ".vdd"] = "default"
        mapping["system.L2" + str(no) + ".Merged_dir"] = "default"
        mapping["system.L2" + str(no) + ".power_gating_vcc"] = "default"

    #If more than 1, change the value
    # ============================================================
    # L3 CACHE MAPPINGS (shared cache)
    # ============================================================
    # If more than 1 L3 cache exists, change the range value
    for no in range(0, 1):
        # L3 Cache Configuration (8 comma-separated values)
        mapping["system.L3" + str(no) + ".L3_config"] = (
            "system.l3.size,"
            "system.l3.tags.block_size,"
            "system.l3.assoc,"
            "system.l3.bank,"
            "system.l3.throughput,"
            "system.l3.response_latency,"
            "system.l3.tags.block_size,"
            "system.l3.cache_policy"
        )

        # L3 Cache Other Parameters
        mapping["system.L3" + str(no) + ".clockrate"] = "default"
        mapping["system.L3" + str(no) + ".ports"] = "default"
        mapping["system.L3" + str(no) + ".device_type"] = "default"
        mapping["system.L3" + str(no) + ".vdd"] = "default"

        # L3 Cache Buffer Sizes (4 comma-separated values - all same)
        mapping["system.L3" + str(no) + ".buffer_sizes"] = (
            "system.l3.mshrs,"
            "system.l3.mshrs,"
            "system.l3.mshrs,"
            "system.l3.mshrs"
        )

        mapping["system.L3" + str(no) + ".Merged_dir"] = "default"
        mapping["system.L3" + str(no) + ".power_gating_vcc"] = "default"

        # ============================================================
        # NoC (Network-on-Chip) MAPPINGS
        # ============================================================
        # Used for multi-core interconnect modeling
        mapping["system.NoC" + str(no) + ".clockrate"] = "default"
        mapping["system.NoC" + str(no) + ".vdd"] = "default"
        mapping["system.NoC" + str(no) + ".power_gating_vcc"] = "default"
        mapping["system.NoC" + str(no) + ".type"] = "default"
        mapping["system.NoC" + str(no) + ".horizontal_nodes"] = "default"
        mapping["system.NoC" + str(no) + ".vertical_nodes"] = "default"
        mapping["system.NoC" + str(no) + ".has_global_link"] = "default"
        mapping["system.NoC" + str(no) + ".link_throughput"] = "default"
        mapping["system.NoC" + str(no) + ".link_latency"] = "default"
        mapping["system.NoC" + str(no) + ".input_ports"] = "default"
        mapping["system.NoC" + str(no) + ".output_ports"] = "default"
        mapping["system.NoC" + str(no) + ".flit_bits"] = "default"
        mapping["system.NoC" + str(no) + ".virtual_channel_per_port"] = "default"
        mapping["system.NoC" + str(no) + ".input_buffer_entries_per_vc"] = "default"
        mapping["system.NoC" + str(no) + ".chip_coverage"] = "default"
        mapping["system.NoC" + str(no) + ".link_routing_over_percentage"] = "default"

    # ============================================================
    # MEMORY CONTROLLER MAPPINGS
    # ============================================================
    mapping["system.mc.type"] = "default"
    mapping["system.mc.vdd"] = "default"
    mapping["system.mc.power_gating_vcc"] = "default"
    mapping["system.mc.mc_clock"] = "system.cpu_clk_domain.clock"
    mapping["system.mc.peak_transfer_rate"] = "default"
    mapping["system.mc.block_size"] = "system.mem_ctrls.write_buffer_size"
    mapping["system.mc.number_mcs"] = "system.mc.number_mcs"
    mapping["system.mc.memory_channels_per_mc"] = "system.mem_ctrls.channels"
    mapping["system.mc.number_ranks"] = "system.mem_ctrls.ranks_per_channel"
    mapping["system.mc.req_window_size_per_channel"] = "default"
    mapping["system.mc.IO_buffer_size_per_channel"] = "default"
    mapping["system.mc.databus_width"] = "default"
    mapping["system.mc.addressbus_width"] = "default"
    mapping["system.mc.withPHY"] = "default"

    # ============================================================
    # NIU (Network Interface Unit) MAPPINGS
    # ============================================================
    mapping["system.niu.type"] = "default"
    mapping["system.niu.vdd"] = "default"
    mapping["system.niu.power_gating_vcc"] = "default"
    mapping["system.niu.clockrate"] = "default"
    mapping["system.niu.number_units"] = "default"

    # ============================================================
    # PCIe MAPPINGS
    # ============================================================
    mapping["system.pcie.type"] = "default"
    mapping["system.pcie.vdd"] = "default"
    mapping["system.pcie.power_gating_vcc"] = "default"
    mapping["system.pcie.withPHY"] = "default"
    mapping["system.pcie.clockrate"] = "default"
    mapping["system.pcie.number_units"] = "default"
    mapping["system.pcie.num_channels"] = "default"

    # ============================================================
    # FLASH CONTROLLER MAPPINGS
    # ============================================================
    mapping["system.flashc.number_flashcs"] = "default"
    mapping["system.flashc.type"] = "default"
    mapping["system.flashc.vdd"] = "default"
    mapping["system.flashc.power_gating_vcc"] = "default"
    mapping["system.flashc.withPHY"] = "default"
    mapping["system.flashc.peak_transfer_rate"] = "default"

    # ============================================================
    # WRITE CONFIG VALUES INTO XML TREE
    # ============================================================
    print("\nWriting values to McPAT XML template...")

    params_processed = 0
    params_defaulted = 0
    params_missing = 0

    for child in root.iter('param'):
        # Get the parameter name and current value from XML
        name = child.attrib['name']
        val = child.attrib['value']

        # Build full path: parent.name (e.g., system.core0.clock_rate)
        name = parent_map[child].attrib['id'] + "." + name

        # Check if this parameter has a mapping
        if name not in mapping:
            print(f"WARNING: No mapping found for {name}")
            continue

        # Get the mapped config path
        mapped_path = mapping[name]

        # ============================================================
        # CASE 1: Default values (no change needed)
        # ============================================================
        if mapped_path == "default":
            continue

        # ============================================================
        # CASE 2: Comma-separated values (multiple config paths)
        # ============================================================
        elif "," in mapped_path:
            mappingArray = mapped_path.split(",")
            ans = ""

            for x in mappingArray:
                findMltVal = getConfValue(x)

                # Special handling: Associativity must be power of 2
                if "assoc" in x and findMltVal != -1 and findMltVal > 0:
                    if findMltVal & (findMltVal - 1):  # Not a power of 2
                        p = 1
                        while p < findMltVal:
                            p <<= 1
                        print(f"  Adjusted associativity from {findMltVal} to {p} (power of 2)")
                        findMltVal = p

                # Special handling: D-cache size must be at least 8KB
                if "dcache.size" in x and findMltVal != -1 and findMltVal > 0:
                    if findMltVal < 8192:
                        print(f"  Adjusted dcache size from {findMltVal} to 8192 (minimum 8KB)")
                        findMltVal = 8192

                # Special handling: I-cache size must be at least 8KB
                if "icache.size" in x and findMltVal != -1 and findMltVal > 0:
                    if findMltVal < 8192:
                        print(f"  Adjusted icache size from {findMltVal} to 8192 (minimum 8KB)")
                        findMltVal = 8192

                # Value not found in config
                if findMltVal == -1:
                    if x in defaultChangedConfigValue:
                        ans += str(defaultChangedConfigValue[x])
                    else:
                        ans += str(1)
                        params_defaulted += 1
                else:
                    if findMltVal is None:
                        findMltVal = 0
                    ans += str(findMltVal)

                ans += ","

            # Remove trailing comma and set value
            child.attrib['value'] = str(ans[:-1])
            params_processed += 1

        # ============================================================
        # CASE 3: Single value not found in config
        # ============================================================
        else:
            foundVal = getConfValue(mapped_path)

            if foundVal == -1:
                # Try to get from defaultChangedConfigValue
                if mapped_path in defaultChangedConfigValue:
                    val = defaultChangedConfigValue[mapped_path]
                    child.attrib['value'] = str(val)
                    params_defaulted += 1
                else:
                    # Last resort: set to 0
                    child.attrib['value'] = "0"
                    params_missing += 1
                    print(f"  WARNING: {name} not found, setting to 0")

            # ============================================================
            # CASE 4: Value found but empty
            # ============================================================
            elif foundVal == "" or foundVal == "[]":
                print(f"  WARNING: {name} value is null/empty in config file, setting to 0")
                child.attrib['value'] = "0"
                params_missing += 1

            # ============================================================
            # CASE 5: Value found and needs parameter transformation
            # ============================================================
            elif mapped_path in params:
                val = params[mapped_path]
                child.attrib['value'] = str(val)
                params_processed += 1

            # ============================================================
            # CASE 6: Value found - use as-is
            # ============================================================
            else:
                val = foundVal
                if val is None:
                    val = 0
                child.attrib['value'] = str(val)
                params_processed += 1

    # ============================================================
    # SUMMARY
    # ============================================================
    print("\n" + "=" * 60)
    print("McPAT XML Generation Complete!")
    print("=" * 60)
    print(f"Parameters processed:  {params_processed}")
    print(f"Parameters defaulted:  {params_defaulted}")
    print(f"Parameters missing:    {params_missing}")
    print(f"Total cores:           {noCores}")
    if l3_exists:
        print(f"L3 cache:              Present ({l3_key})")
    else:
        print(f"L3 cache:              Not present")
    print("=" * 60)
    print("Done")

def getConfValue(confStr):
    """
    Extract value from NEW gem5 config format (board-based).

    Translates OLD-style paths (system.cpu0.X) to NEW paths (board.processor.cores0.core.X)

    Args:
        confStr: Dot-separated path like "system.cpu0.fetchWidth"

    Returns:
        Value from config, or -1 if not found
    """
    global config

    # Validate input
    if "," in confStr:
        return -1

    # Extract core number from path (e.g., "system.cpu0.xxx" → core 0)
    coreNo = 0
    import re
    match = re.search(r'cpu(\d+)', confStr)
    if match:
        coreNo = int(match.group(1))

    # ============================================================
    # PATH TRANSLATION: OLD format → NEW format
    # ============================================================

    # System-level translations (no core index)
    if confStr == "system.cpu_clk_domain.clock":
        confStr = "board.clk_domain.clock"

    elif confStr.startswith("system.mem_ctrls"):
        # system.mem_ctrls.X → board.memory.mem_ctrl.0.dram.X
        rest = confStr.replace("system.mem_ctrls.", "")
        confStr = f"board.memory.mem_ctrl.0.dram.{rest}"

    elif confStr.startswith("system.l3"):
        # system.l3.X → board.cache_hierarchy.l3.X (if L3 exists)
        rest = confStr.replace("system.l3.", "")
        confStr = f"board.cache_hierarchy.l3.{rest}"

    # Per-core translations
    elif f"system.cpu{coreNo}" in confStr:
        rest = confStr.replace(f"system.cpu{coreNo}.", "")

        # CPU core parameters
        if not any(cache in rest for cache in ["icache", "dcache", "l2cache"]):
            if rest.startswith("isa"):
                # system.cpu0.isa.type → board.processor.cores0.core.isa.0.type
                rest = rest.replace("isa.", "isa.0.")
                confStr = f"board.processor.cores{coreNo}.core.{rest}"
            elif rest.startswith("branchPred"):
                # Handle branch predictor special cases
                if "RASSize" in rest:
                    confStr = f"board.processor.cores{coreNo}.core.branchPred.ras.numEntries"
                elif "BTBEntries" in rest:
                    confStr = f"board.processor.cores{coreNo}.core.branchPred.btb.numEntries"
                elif "BTBTagSize" in rest:
                    confStr = f"board.processor.cores{coreNo}.core.branchPred.btb.tagBits"
                elif "indirectWays" in rest:
                    confStr = f"board.processor.cores{coreNo}.core.branchPred.indirectBranchPred.indirectWays"
                else:
                    # Other branch predictor params stay as-is
                    confStr = f"board.processor.cores{coreNo}.core.{rest}"
            elif rest.startswith("itb") or rest.startswith("dtb"):
                # system.cpu0.itb.X → board.processor.cores0.core.mmu.itb.X
                confStr = f"board.processor.cores{coreNo}.core.mmu.{rest}"
            else:
                # Regular CPU params
                confStr = f"board.processor.cores{coreNo}.core.{rest}"

        # Cache translations
        elif "icache" in rest:
            # system.cpu0.icache.X → board.cache_hierarchy.l1i-cache-0.X
            cache_param = rest.replace("icache.", "")
            confStr = f"board.cache_hierarchy.l1i-cache-{coreNo}.{cache_param}"

        elif "dcache" in rest:
            # system.cpu0.dcache.X → board.cache_hierarchy.l1d-cache-0.X
            cache_param = rest.replace("dcache.", "")
            confStr = f"board.cache_hierarchy.l1d-cache-{coreNo}.{cache_param}"

        elif "l2cache" in rest:
            # system.cpu0.l2cache.X → board.cache_hierarchy.l2-cache-0.X
            cache_param = rest.replace("l2cache.", "")
            confStr = f"board.cache_hierarchy.l2-cache-{coreNo}.{cache_param}"

    # ============================================================
    # NAVIGATE CONFIG WITH TRANSLATED PATH
    # ============================================================

    confStrArray = confStr.split(".")
    currentConfig = config

    for i, component in enumerate(confStrArray):
        if currentConfig is None:
            return -1

        # Handle array indexing by number (e.g., "cores0" → cores[0])
        if component.startswith("cores") and component[5:].isdigit():
            idx = int(component[5:])
            if "cores" in currentConfig and isinstance(currentConfig["cores"], list):
                if idx < len(currentConfig["cores"]):
                    currentConfig = currentConfig["cores"][idx]
                else:
                    return -1
            else:
                return -1

        # Handle cache indexing (e.g., "l1i-cache-0" → direct access)
        elif component.startswith("l1i-cache-") or component.startswith("l1d-cache-") or component.startswith(
                "l2-cache-"):
            if component in currentConfig:
                currentConfig = currentConfig[component]
            else:
                return -1

        # Handle mem_ctrl array
        elif component == "mem_ctrl" and isinstance(currentConfig.get(component), list):
            currentConfig = currentConfig[component][0]

        # Handle ISA array
        elif component == "isa" and isinstance(currentConfig.get(component), list):
            currentConfig = currentConfig[component]

        # Handle numeric array index (e.g., "0" after "isa")
        elif component.isdigit() and isinstance(currentConfig, list):
            idx = int(component)
            if idx < len(currentConfig):
                currentConfig = currentConfig[idx]
            else:
                return -1

        # Normal dictionary navigation
        elif isinstance(currentConfig, dict) and component in currentConfig:
            currentConfig = currentConfig[component]

        # Component not found
        else:
            return -1

    # ============================================================
    # UNWRAP RESULT
    # ============================================================

    # Unwrap single-element arrays (e.g., "clock": [1000] → 1000)
    if isinstance(currentConfig, list):
        if len(currentConfig) == 1:
            return currentConfig[0]
        elif len(currentConfig) == 0:
            return -1

    return currentConfig


# ============================================================
# HELPER FUNCTION (optional - for debugging)
# ============================================================

def debugConfValue(confStr):
    """Debug helper to see path translation"""
    print(f"Original path: {confStr}")
    value = getConfValue(confStr)
    print(f"Value: {value}")
    return value




def writeStatValue(mcpatTemplateFile):
    global stats, tree, noCores
    resolved = build_core_mappings_v25(stats, noCores)
    applied = apply_resolved_to_xml(tree, resolved)
    tree.write("config.xml")
    print(f"Output written to: config.xml")
# ============================================================
# HELPER FUNCTION FOR NEW FORMAT TRANSLATION
# ============================================================
def getStatValueWithTranslation(stat_path):
    """
    Get stat value with automatic NEW format translation

    Args:
        stat_path: OLD-style stat path

    Returns:
        Stat value or 0 if not found
    """
    global stats

    # Already tried exact match, now try NEW format translations

    # Extract core number if present
    core_match = re.search(r'\.cpu(\d+)\.', stat_path)
    core_num = int(core_match.group(1)) if core_match else None

    # Cache stats translations
    if core_num is not None:
        if ".icache." in stat_path:
            # system.cpu0.icache.X → board.cache_hierarchy.l1i-cache-0.X
            new_path = stat_path.replace(
                f"system.cpu{core_num}.icache.",
                f"board.cache_hierarchy.l1i-cache-{core_num}."
            )
            if new_path in stats:
                return stats[new_path]

        elif ".dcache." in stat_path:
            # system.cpu0.dcache.X → board.cache_hierarchy.l1d-cache-0.X
            new_path = stat_path.replace(
                f"system.cpu{core_num}.dcache.",
                f"board.cache_hierarchy.l1d-cache-{core_num}."
            )
            if new_path in stats:
                return stats[new_path]

        elif ".l2cache." in stat_path:
            # system.cpu0.l2cache.X → board.cache_hierarchy.l2-cache-0.X
            new_path = stat_path.replace(
                f"system.cpu{core_num}.l2cache.",
                f"board.cache_hierarchy.l2-cache-{core_num}."
            )
            if new_path in stats:
                return stats[new_path]

        # CPU/Core stats
        else:
            # system.cpu0.X → board.processor.cores0.core.X
            new_path = stat_path.replace(
                f"system.cpu{core_num}.",
                f"board.processor.cores{core_num}.core."
            )
            if new_path in stats:
                return stats[new_path]

    # L3 cache
    elif ".l3." in stat_path:
        new_path = stat_path.replace(
            "system.l3.",
            f"board.cache_hierarchy.{l3_key}." if l3_exists else "board.cache_hierarchy.l3."
        )
        if new_path in stats:
            return stats[new_path]

    # Memory controller
    elif ".mem_ctrls." in stat_path:
        # Try multiple possible NEW format paths
        param = stat_path.split(".")[-1]

        possible_paths = [
            f"board.memory.mem_ctrl.0.dram.{param}",
            f"board.memory.mem_ctrl.0.{param}",
        ]

        for new_path in possible_paths:
            if new_path in stats:
                return stats[new_path]

    # Not found in any format
    return 0


# Goran: completed indentation for pretty print
def indent(elem, level=0):
    #we are spacing xml-tree with specific format
    #If we are in root and we got sub component of root that is system then we add space before system component
    #so for tail we are decreasing space before component

    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i



if __name__ == '__main__':
    main()
