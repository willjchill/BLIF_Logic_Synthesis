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

Similar to "input" and "output" in Verilog.

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

The BLIF parsing and construction of a DAG representing the circuit will be done in Python. To use the parser, do the following:

`synth.py <file.blif> --model <model name>`

Note that the model flag is optional. If model flag is not included, it will try to synthesize the first model that appears in the BLIF. If no model is defined (and only .names is), then the first .names that appears in the BLIF will be simulated.

This will do two things:

A. Generate a standard output for various metrics (described more in section 2.3).

B. Generate a valid structural Verilog file that can be synthesized and implemented on any FPGA. The verilog file will be called `top.v` for simplicity. All of the subcircuits defined in the BLIF will be inlined to the top module during parsing and logic synthesis.

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
11. Custom Command #1: A feature/command of your choice (e.g., hazard detection, delay estimation, XOR/XNOR factorization, truth table exporter).
12. Custom Command #2: A second feature/command of your choice.

These metrics will be output to a file called `metrics.txt`. 

### 3. Project Hierarchy

```
.
├── README.md
├── src
│   ├── minimizer
│   ├── parser
│   ├── synth.py
│   └── verilate
├── startup.sh
└── test_BLIF
```

The main script to run the program is `synth.py`, contained in src. `startup.sh` should create a Python environment and install any necessary packages before running the program using bash. Our custom modules for this program are split among minimizer, parser, and verilate. 

- **Minimizer** contains modules for DAG representation of logic as well as various methods of minimizing logic such as QM. 

- **Parser** contains modules to parse constrained BLIF files. 

- **Verilate** contains conversion from DAG representation to structural Verilog.

----------------------------------------------------------------------------------------

Last Updated 10/6/2026

**Based off of Boston University's EC551 - Programming Assignment 1**
