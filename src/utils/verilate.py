from pathlib import Path

"""
    Generates structural Verilog AND/INV/OR primitive gates for a single SOP expression.
    - output_name: name of the output signal
    - inputs: list of input variable names (ordered)
    - minterms: list of binary minterm strings, e.g. ['01', '10']
"""
def sopToVerilogGates(output_name: str, inputs: list[str], minterms: list[str]) -> list[str]:
    lines = []
    lines.append(f"    // Logic for output: {output_name}")

    # Constant 0: no minterms
    if not minterms:
        lines.append(f"    buf buf_{output_name} ({output_name}, 1'b0);")
        return lines

    # Constant 1: all minterms present
    if len(minterms) == (1 << len(inputs)):
        lines.append(f"    buf buf_{output_name} ({output_name}, 1'b1);")
        return lines

    # Identify which input variables need inverters
    inverted_vars = set()
    for m in minterms:
        for var, bit in zip(inputs, m):
            if bit == "0":
                inverted_vars.add(var)

    # 1. INV gates
    for var in sorted(inverted_vars):
        inv_wire = f"{output_name}_not_{var}"
        lines.append(f"    wire {inv_wire};")
        lines.append(f"    not inv_{output_name}_{var} ({inv_wire}, {var});")

    # 2. AND gates for product terms
    if len(minterms) == 1:
        m = minterms[0]
        lits = []
        for var, bit in zip(inputs, m):
            if bit == "1":
                lits.append(var)
            elif bit == "0":
                lits.append(f"{output_name}_not_{var}")

        if not lits:
            lines.append(f"    buf buf_{output_name} ({output_name}, 1'b1);")
        elif len(lits) == 1:
            lines.append(f"    buf buf_{output_name} ({output_name}, {lits[0]});")
        else:
            lines.append(f"    and and_{output_name} ({output_name}, {', '.join(lits)});")
    else:
        prod_wires = []
        for i, m in enumerate(minterms):
            p_wire = f"{output_name}_p{i}"
            prod_wires.append(p_wire)
            lines.append(f"    wire {p_wire};")

            lits = []
            for var, bit in zip(inputs, m):
                if bit == "1":
                    lits.append(var)
                elif bit == "0":
                    lits.append(f"{output_name}_not_{var}")

            if not lits:
                lines.append(f"    buf buf_{output_name}_{i} ({p_wire}, 1'b1);")
            elif len(lits) == 1:
                lines.append(f"    buf buf_{output_name}_{i} ({p_wire}, {lits[0]});")
            else:
                lines.append(f"    and and_{output_name}_{i} ({p_wire}, {', '.join(lits)});")

        # 3. OR gate to combine product terms
        lines.append(f"    or or_{output_name} ({output_name}, {', '.join(prod_wires)});")

    return lines


"""
    Generates structural Verilog module using SOP metrics
"""
def generateVerilog(inputs: list[str], outputs: list[str], metrics: dict, module_name: str = "top") -> str:
    lines = []
    lines.append("// Structural Verilog generated from BLIF metrics")
    lines.append(f"module {module_name} (")

    port_decls = []
    for inp in inputs:
        port_decls.append(f"    input wire {inp}")
    for out in outputs:
        port_decls.append(f"    output wire {out}")
    lines.append(",\n".join(port_decls))
    lines.append(");")
    lines.append("")

    for out in outputs:
        minterms = metrics[out]["Canonical SOP"]
        gate_lines = sopToVerilogGates(out, inputs, minterms)
        lines.extend(gate_lines)
        lines.append("")

    lines.append("endmodule")
    lines.append("")
    return "\n".join(lines)


"""
    Writes structural Verilog to file
"""
def writeVerilog(inputs: list[str], outputs: list[str], metrics: dict, filePath: Path, module_name: str = "top") -> None:
    code = generateVerilog(inputs, outputs, metrics, module_name)
    with filePath.open("w", encoding="utf-8") as f:
        f.write(code)
