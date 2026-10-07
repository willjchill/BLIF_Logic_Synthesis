# Logic Synthesis Project

## 1. Project Objective

The objective of this project is to use an open-source logic format in generate synthesizable *structural* Verilog code. This Verilog code should be synthisizable on any FPGA in order for it to be valid.

## 2. Project Features

### 2.1. BLIF Constraints

[BLIF](https://www.cs.columbia.edu/~cs6861/sis/blif/index.html) will be used as inspiration on how the logic will be defined in an input file. These input files will have the `.blif` extension, **although will not have all the original features of the format**.

These are the features that will be included in our custom BLIF parser:

1. We will **only** use combinational logic. No clocks, latches, or states allowed in BLIF.

2. The only commands allowed are 

- `.model <name>`

Similar to "module" in Verilog.

- `.{inputs/outputs} <pinName_0> <pinName_1> .. <pinName_N>`

Similar to "input" and "output" in Verilog. All module and I/O names should be unique. If there is a duplicate, an error will be raised.

- `.subckt <in0> <in1> ... <inN> <out0> <out1> ... <outN>`

Instantiate a model within another model. You can define the model wherever in the BLIF file.

- `.names <in0> <in1> <out>` 

This will define a boolean expression. We will only allow for SOP definition.

- `.end`

This is NECESSARY for our parser. BLIF typically does not mind if you omit `.end` but to avoid ambiguity we will require this for every .model block. Think of it as adding "endmodule" and the end of a module definition in Verilog.

- Comments can be added using # symbol.

While BLIF format typically allows for the omission of `.inputs` and `.outputs`, this parser *will* require you to define them if you have a `.model` command. Whenever you define .model, you MUST also define .inputs, .outputs, and .end. This is to avoid ambiguity and many headaches when debugging our logic synthesis program.

Example of BLIF half-adder. Note that we describe each output of half-adder in terms of SOP:

```
.model half_adder 
.inputs a b
.outputs sum cout

# SOP for sum
.names a b sum 
01 1
10 1

# SOP for carry out bit 
.names a b cout
11 1

.end
```

### 2.2. Python Parser Usage

The BLIF parsing and construction of a std data structure representing the circuit will be done in Python. To use the parser, do the following:

`python3 src/synth.py <file.blif> --model <model name>`

Note that the model flag is optional. If model flag is not included, it will try to synthesize the first model that appears in the BLIF. If no model is defined (and only .names is), then the first .names that appears in the BLIF will be simulated.

This will do two things:

A. Generate a standard output for various metrics saved under `output/metrics/metrics_<model>_<timestamp>.txt`.

B. Generate structural Verilog and simulation testbench files organized under `output/verilog/{model_name | top}_{timestamp}/`:
   - `top_{timestamp}.v`: Valid structural Verilog file that can be synthesized and implemented on any FPGA. All subcircuits defined in the BLIF are inlined to the top module during parsing and logic synthesis.
   - `tb_top_{timestamp}.v`: Verilog simulation testbench that probes all $2^N$ input combinations, tests outputs against the canonical SOP golden logic using assertions, prints pass/fail results for each vector, and dumps waveforms to `tb_top_{timestamp}.vcd`.

### 2.3. Output Metrics Reported

1. Canonical SOP: Compute and display the canonical Sum-of-Products form.
2. Canonical POS: Compute and display the canonical Product-of-Sums form.
3. Inverse Canonical SOP: Compute and display the canonical SOP form for the inverse function (𝐹̅ ).
4. Inverse Canonical POS: Compute and display the canonical POS form for the inverse function (𝐹̅ ).
5. Literal Minimized SOP: Return a minimized SOP representation (e.g., using Quine-McCluskey, Espresso-like algorithms, or K-map minimization).
- Metric: Report the number of literals saved vs. the canonical SOP version.
6. Literal Minimized POS: Return a minimized POS representation.
- Metric: Report the number of literals saved vs. the canonical POS version.
7. Prime Implicants: Report the total count of Prime Implicants.
8. Essential Prime Implicants: Report the total count of Essential Prime Implicants.
9. ON-Set Minterms: Report the total number of ON-Set minterms (Σ𝑚).
10. OFF-Set Maxterms: Report the total number of OFF-Set maxterms (Π𝑀).
11. Custom Command #1: Delay Estimation (circuit logic depth in gate levels).
12. Custom Command #2: Truth Table Exporter (complete input-output truth table).

These metrics will be output to a file called `output/metrics/metrics_<model>_<timestamp>.txt`. 

### 2.4. Simulation & Waveform Verification

To simulate the synthesized design and view waveforms in GTKWave:

```bash
cd output/verilog/<model_name | top>_<timestamp>
iverilog -g2012 -o sim top_<timestamp>.v tb_top_<timestamp>.v
vvp sim
gtkwave tb_top_<timestamp>.vcd
```

### 2.5. Vivado FPGA Synthesis, Implementation & Bitstream

To automatically synthesize, implement, generate bitstream, and program the design onto a Xilinx Artix-7 FPGA (`xc7a100tcsg324-1` on Digilent Nexys 4 DDR), use `vivadoSynth.tcl`:

```bash
# Run with Vivado in batch mode (automatically picks the most recent Verilog run directory):
vivado -mode batch -source vivadoSynth.tcl

# Or specify a specific output directory:
vivado -mode batch -source vivadoSynth.tcl -tclargs --output_dir output/verilog/<model>_<timestamp>

# Or directly execute the script:
./vivadoSynth.tcl [--output_dir <path>]
```

Features:
- **Automatic I/O Mapping**: Inputs are automatically mapped in order to Nexys 4 DDR switches (`SW[0]`, `SW[1]`, ...), and outputs are automatically mapped to LEDs (`LED[0]`, `LED[1]`, ...).
- **Target Part**: `xc7a100tcsg324-1` (Artix-7, Package `csg324`, Speed `-1`).
- **Constraints**: Generates `auto_pins.xdc` inside the Verilog run directory referencing board pins from `output/verilog/Nexys4DDR_Master.xdc`.
- **Hardware Programming**: Connects to the Vivado Hardware Manager and automatically programs connected FPGA hardware.
- **Reporting**: Logs full execution status, debug details, and FPGA I/O pin mappings to `output/fpga/report_<timestamp>.log`.

### 3. Project Hierarchy

```
.
├── README.md
├── .gitignore
├── vivadoSynth.tcl
├── output
│   ├── fpga
│   │   └── report_<timestamp>.log
│   ├── metrics
│   │   └── metrics_<model>_<timestamp>.txt
│   └── verilog
│       ├── Nexys4DDR_Master.xdc
│       └── <model>_<timestamp>
│           ├── auto_pins.xdc
│           ├── top_<timestamp>.v
│           ├── tb_top_<timestamp>.v
│           └── top.bit (generated by Vivado)
├── src
│   ├── synth.py
│   └── utils
│       ├── blifParser.py
│       ├── logicDAG.py
│       ├── sopMin.py
│       └── verilate.py
└── test_BLIF
    ├── fullAdder.blif
    └── halfAdder.blif
```

The main script to run the program is `synth.py`, contained in src. It uses only default Python standard library packages and requires no external dependencies. Our custom modules for this program are split among minimizer, parser, and verilate. 

- **logicDAG / sopMIN** contains modules for circuit representation of logic as well as various methods of minimizing logic such as QM. 

- **blifParser** contains modules to parse constrained BLIF files. 

- **verilate** contains conversion from circuit representation to structural Verilog and simulation testbench generation.

- **vivadoSynth.tcl** automates Vivado FPGA synthesis, implementation, bitstream generation, and hardware programming for the Nexys 4 DDR board.


----------------------------------------------------------------------------------------

Last Updated 10/7/2026

**Based off of Boston University's EC551 - Programming Assignment 1**
