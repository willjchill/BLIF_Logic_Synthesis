import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add src and src/utils to path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "utils"))

try:
    import utils.blifParser as prs
    import utils.logicDAG as ld
    import utils.verilate as vrt
except ImportError:
    import blifParser as prs
    import logicDAG as ld
    import verilate as vrt

if __name__ == "__main__":
    # step 1: parse command line

    # <synth.py> <file.blif> --model <name>
    commandParser = argparse.ArgumentParser(description="Usage synth.py <file.blif> --model <name>.")
    commandParser.add_argument("input_file", type=Path, help="Path to source file")
    commandParser.add_argument("--model", type=str, default='', help="OPTIONAL: Name of model that is being synthesized. Defaults to first model if it exists. If no model exists, default to first names command.")

    args = commandParser.parse_args()

    # invariants
    if not args.input_file.is_file():
        raise ValueError("File does not exist.")
    if args.input_file.name[-5:] != ".blif":
        raise ValueError("File must contain .blif extension.") 

    # step 2: parse blif file
    commandList = prs.getCommandList(args.input_file)
    modelList = prs.modelListConstructor(commandList)

    if args.model:
        if args.model not in modelList:
            raise ValueError(f"Model '{args.model}' not found in BLIF file.")
        selectedModel = modelList[args.model]
    elif modelList:
        selectedModel = next(iter(modelList.values()))
    else:
        raise ValueError("No models found in BLIF file.")

    # flatten subcircuits into gates
    selectedModel.flattenModel(modelList)

    # step 3: build DAG 
    cktDAG = ld.TopCktDAG(selectedModel.inputs, selectedModel.outputs)
    cktDAG.model2DAG(selectedModel)

    # Output directory setup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    moduleName = selectedModel.name if selectedModel.name else "top"

    projectRoot = Path(__file__).resolve().parent.parent
    outputDir = projectRoot / "output"
    metricsDir = outputDir / "metrics"
    verilogDir = outputDir / "verilog"
    verilogRunDir = verilogDir / f"{moduleName}_{timestamp}"
    metricsDir.mkdir(parents=True, exist_ok=True)
    verilogRunDir.mkdir(parents=True, exist_ok=True)

    metricsFile = metricsDir / f"metrics_{moduleName}_{timestamp}.txt"
    verilogFile = verilogRunDir / f"top_{timestamp}.v"
    tbFile = verilogRunDir / f"tb_top_{timestamp}.v"

    # step 4: report metrics
    cktDAG.evalMetrics()
    metricsOutput = cktDAG.formatMetrics()
    with metricsFile.open("w", encoding="utf-8") as f:
        f.write(metricsOutput)
    print(f"Metrics written to {metricsFile}")

    # step 5: output structural verilog and simulation testbench
    vrt.writeVerilog(cktDAG.inputs, cktDAG.outputs, cktDAG.metrics, verilogFile, module_name="top")
    print(f"Structural Verilog written to {verilogFile}")

    vrt.writeTestbench(cktDAG.inputs, cktDAG.outputs, cktDAG.metrics, tbFile, module_name="top", timestamp=timestamp)
    print(f"Simulation testbench written to {tbFile}")

