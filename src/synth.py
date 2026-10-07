import parser.blifParser as prs
import argparse
from pathlib import Path

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

    print(args.input_file, type(args.input_file))
    print(args.model)

    # step 2: parse blif file
    with args.input_file.open("r", encoding="utf-8") as file:
        for line in file:
            print(line.rstrip("\n"))

    # step 3: build DAG 

    # step 4: report metrics

    # step 5: output structural verilog
