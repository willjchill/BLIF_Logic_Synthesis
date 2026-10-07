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


"""
    Generates Verilog testbench simulating all combinations of inputs,
    asserting outputs against canonical SOP golden logic, and dumping waveform.
"""
def generateTestbench(inputs: list[str], outputs: list[str], metrics: dict, module_name: str = "top", timestamp: str = "") -> str:
    n_in = len(inputs)
    n_out = len(outputs)
    total_comb = 1 << n_in

    tb_lines = []
    tb_lines.append("`timescale 1ns/1ps")
    tb_lines.append("")
    tb_lines.append(f"// Simulation testbench for {module_name}")
    tb_lines.append("// Probes all 2^N combinations against canonical SOP golden logic")
    if timestamp:
        tb_lines.append(f"// Timestamp: {timestamp}")
    tb_lines.append("")
    tb_lines.append("module tb_top;")
    tb_lines.append("")
    tb_lines.append("    // Inputs to DUT")
    for inp in inputs:
        tb_lines.append(f"    reg {inp};")
    tb_lines.append("")
    tb_lines.append("    // Outputs from DUT")
    for out in outputs:
        tb_lines.append(f"    wire {out};")
    tb_lines.append("")
    tb_lines.append("    // Golden expected outputs")
    for out in outputs:
        tb_lines.append(f"    reg {out}_expected;")
    tb_lines.append("")
    tb_lines.append("    // Test tracking")
    tb_lines.append("    integer total_tests = 0;")
    tb_lines.append("    integer failed_tests = 0;")
    tb_lines.append("")
    tb_lines.append(f"    // Instantiate Device Under Test ({module_name})")
    tb_lines.append(f"    {module_name} dut (")
    port_maps = [f"        .{p}({p})" for p in inputs + outputs]
    tb_lines.append(",\n".join(port_maps))
    tb_lines.append("    );")
    tb_lines.append("")

    # Task to check a vector
    in_vec_decl = f"input [{n_in - 1}:0] in_vec" if n_in > 1 else "input [0:0] in_vec"
    exp_vec_decl = f"input [{n_out - 1}:0] exp_vec" if n_out > 1 else "input [0:0] exp_vec"
    in_unpack = f"{{{', '.join(inputs)}}}" if n_in > 1 else inputs[0]
    exp_unpack = f"{{{', '.join(f'{out}_expected' for out in outputs)}}}" if n_out > 1 else f"{outputs[0]}_expected"

    tb_lines.append("    // Task to apply vector, check assertions, and log results")
    tb_lines.append("    task check_vector(")
    tb_lines.append(f"        {in_vec_decl},")
    tb_lines.append(f"        {exp_vec_decl}")
    tb_lines.append("    );")
    tb_lines.append("    begin")
    tb_lines.append(f"        {in_unpack} = in_vec;")
    tb_lines.append(f"        {exp_unpack} = exp_vec;")
    tb_lines.append("        #10;")
    tb_lines.append("        total_tests = total_tests + 1;")
    tb_lines.append("")

    for out in outputs:
        tb_lines.append(f"        assert ({out} === {out}_expected) else begin")
        tb_lines.append(f"            $error(\"ASSERTION FAILED at %0t for {out}: inputs=%b, expected %b, got %b\", $time, in_vec, {out}_expected, {out});")
        tb_lines.append("            failed_tests = failed_tests + 1;")
        tb_lines.append("        end")

    tb_lines.append("")
    pass_cond = " && ".join(f"({out} === {out}_expected)" for out in outputs)
    inputs_header = ", ".join(inputs)
    outputs_display = " ".join(f"{out}=%b (exp %b)" for out in outputs)
    outputs_args = ", ".join([f"{out}, {out}_expected" for out in outputs])

    tb_lines.append(f"        if ({pass_cond}) begin")
    tb_lines.append(f"            $display(\"[PASS] Time=%0t | Inputs {{{inputs_header}}}=%b | {outputs_display}\", $time, in_vec, {outputs_args});")
    tb_lines.append("        end else begin")
    tb_lines.append(f"            $display(\"[FAIL] Time=%0t | Inputs {{{inputs_header}}}=%b | {outputs_display} [MISMATCH]\", $time, in_vec, {outputs_args});")
    tb_lines.append("        end")
    tb_lines.append("    end")
    tb_lines.append("    endtask")
    tb_lines.append("")

    # Waveform dumping
    vcd_name = f"tb_top_{timestamp}.vcd" if timestamp else "tb_top.vcd"
    tb_lines.append("    // Waveform dump for GTKWave")
    tb_lines.append("    initial begin")
    tb_lines.append(f'        $dumpfile("{vcd_name}");')
    tb_lines.append("        $dumpvars(0, tb_top);")
    tb_lines.append("    end")
    tb_lines.append("")

    # Stimulus block
    tb_lines.append("    // Simulation stimulus")
    tb_lines.append("    initial begin")
    tb_lines.append("        total_tests = 0;")
    tb_lines.append("        failed_tests = 0;")
    tb_lines.append("")
    tb_lines.append('        $display("================================================================================");')
    tb_lines.append(f'        $display("STARTING SIMULATION: Testing all {total_comb} input combinations for {module_name}");')
    tb_lines.append('        $display("================================================================================");')
    tb_lines.append("")

    for i in range(total_comb):
        comb = f"{i:0{n_in}b}"
        exp_bits = []
        active_outs = []
        for out in outputs:
            minterms = set(metrics.get(out, {}).get("Canonical SOP", []))
            if comb in minterms:
                exp_bits.append("1")
                active_outs.append(out)
            else:
                exp_bits.append("0")
        exp_comb = "".join(exp_bits)
        comment_info = f"// Vector {i}: {inputs_header} = {comb}"
        if active_outs:
            comment_info += f" -> ON-set minterm active for ({', '.join(active_outs)})"
        else:
            comment_info += " -> OFF-set for all outputs"
        tb_lines.append(f"        {comment_info}")
        tb_lines.append(f"        check_vector({n_in}'b{comb}, {n_out}'b{exp_comb});")

    tb_lines.append("")
    tb_lines.append("        #10;")
    tb_lines.append('        $display("================================================================================");')
    tb_lines.append("        if (failed_tests == 0) begin")
    tb_lines.append('            $display("ALL %0d ASSERTIONS PASSED! Simulation successful.", total_tests);')
    tb_lines.append("        end else begin")
    tb_lines.append('            $display("SIMULATION FAILED: %0d / %0d assertions failed.", failed_tests, total_tests);')
    tb_lines.append("        end")
    tb_lines.append('        $display("================================================================================");')
    tb_lines.append("        $finish;")
    tb_lines.append("    end")
    tb_lines.append("")
    tb_lines.append("endmodule")
    tb_lines.append("")

    return "\n".join(tb_lines)


"""
    Writes simulation testbench to file
"""
def writeTestbench(inputs: list[str], outputs: list[str], metrics: dict, filePath: Path, module_name: str = "top", timestamp: str = "") -> None:
    code = generateTestbench(inputs, outputs, metrics, module_name, timestamp)
    with filePath.open("w", encoding="utf-8") as f:
        f.write(code)

