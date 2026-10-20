from collections import deque
from pathlib import Path

try:
    import utils.blifParser as blifParser
    import utils.sopMin as sopMin
except ImportError:
    import blifParser
    import sopMin

# DAG connecting all of gates / modules in ckt
class TopCktDAG(object):
    def __init__(self, inputs: list[str], outputs: list[str]):
        # variable list contains name : value it resolves to while doing BFS in DAG 
        # need to set init values before walking through tree
        self.varList = {} 
        # top-level inputs
        self.inputs = inputs

        # top-level outputs -- we'll need this if we're going to update metrics dictionary later
        self.outputs = outputs
        self.initNodes = []
        self.nodes = []
        self.q = deque()

        # dictionary of all metrics we can use for output - dictionary of dictionaries
        # "output name" : { dictionary of metrics } 
        self.metrics = {output: {"Canonical SOP": [], 
                                 "Canonical POS": [], 
                                 "Inverse Canonical SOP": [],
                                 "Inverse Canonical POS": [],
                                 "Literal Minimized SOP": [], 
                                 "Literal Minimized POS": [], 
                                 "Prime Implicants": [],
                                 "Essential Prime Implicants": [],
                                 "ON-Set Minterms": 0,
                                 "OFF-Set Maxterms": 0,
                                 "SOP Literals Saved": 0,
                                 "POS Literals Saved": 0
                                 } for output in self.outputs}

    """
        inputLiteral = sets all inputs in order, last in list is MSB
        ex: self.inputs = ["a", "b"]
        if I want a=0, b=1 --> "10"

        just initializes the var list for you
        contains a dictionary of what all the var are evaluated to
    """
    def eval(self, inputLiteral: str) -> None:
        self.varList = {}
        for i in range(len(inputLiteral)):
            self.varList[self.inputs[i]] = inputLiteral[i]

        explored = set()

        for n in self.initNodes:
            self.q.append(n)
            explored.add(n.uniqueID)
 
        # BFS algorithm to evaluate all the intermediates nodes from inputs -> outputs
        while self.q:
            currentNode = self.q.popleft()
            tmpInput = "".join([self.varList[c] for c in currentNode.inputs])
            self.varList[currentNode.output] = currentNode.eval(tmpInput)
            for n in currentNode.nextNodes:
                if n.uniqueID not in explored and all(c in self.varList for c in n.inputs):
                    self.q.append(n)
                    explored.add(n.uniqueID)

    """
        converts models/gates notation from BLIF format --> our std DAG structure
        should set all the appropiate attributes in this DAG 
    """
    def model2DAG(self, top_model) -> None:
        self.inputs = list(top_model.inputs)
        self.outputs = list(top_model.outputs)
        self.metrics = {output: {"Canonical SOP": [], 
                                 "Canonical POS": [], 
                                 "Inverse Canonical SOP": [],
                                 "Inverse Canonical POS": [],
                                 "Literal Minimized SOP": [], 
                                 "Literal Minimized POS": [], 
                                 "Prime Implicants": [],
                                 "Essential Prime Implicants": [],
                                 "ON-Set Minterms": 0,
                                 "OFF-Set Maxterms": 0,
                                 "SOP Literals Saved": 0,
                                 "POS Literals Saved": 0
                                 } for output in self.outputs}

        self.nodes = []
        producer_map = {}

        for gate in top_model.gates:
            out_wire = gate.outputs[0] if gate.outputs else ""
            node = Node(set(gate.minTerms), list(gate.inputs), out_wire, name=gate.id)
            self.nodes.append(node)
            if out_wire:
                producer_map[out_wire] = node

        for node in self.nodes:
            for inp in node.inputs:
                if inp in producer_map:
                    producer_map[inp].nextNodes.append(node)

        self.initNodes = [n for n in self.nodes if all(inp in self.inputs for inp in n.inputs)]

    """
        Updates dictionary with all required metrics, saving it in metrics attribute 
    """
    def evalMetrics(self) -> None:
        bitWidth = len(self.inputs)
        allInputComb = [f"{i:0{bitWidth}b}" for i in range(1 << bitWidth)]

        for output in self.outputs:
            self.metrics[output]["Canonical SOP"] = []
            self.metrics[output]["Canonical POS"] = []
            self.metrics[output]["Inverse Canonical SOP"] = []
            self.metrics[output]["Inverse Canonical POS"] = []

            for input in allInputComb:
                self.eval(input)
                if self.varList.get(output, "0") == "1":
                    self.metrics[output]["Canonical SOP"].append(input)
                    self.metrics[output]["Inverse Canonical POS"].append(input)
                else:
                    self.metrics[output]["Canonical POS"].append(input)
                    self.metrics[output]["Inverse Canonical SOP"].append(input)

            self.metrics[output]["ON-Set Minterms"] = len(self.metrics[output]["Canonical SOP"])
            self.metrics[output]["OFF-Set Maxterms"] = len(self.metrics[output]["Canonical POS"])

            onSet = self.metrics[output]["Canonical SOP"]
            offSet = self.metrics[output]["Canonical POS"]
            primes = sopMin.quineMcCluskey(onSet, bitWidth)
            self.metrics[output]["Prime Implicants"] = primes
            self.metrics[output]["Essential Prime Implicants"] = sopMin.essentialPrimeImplicants(primes, onSet)
            self.metrics[output]["Literal Minimized SOP"] = sopMin.minimizeSOP(onSet, bitWidth)
            self.metrics[output]["Literal Minimized POS"] = sopMin.minimizePOS(offSet, bitWidth)
            self.metrics[output]["SOP Literals Saved"] = bitWidth * len(onSet) - sopMin.literalCount(self.metrics[output]["Literal Minimized SOP"])
            self.metrics[output]["POS Literals Saved"] = bitWidth * len(offSet) - sopMin.literalCount(self.metrics[output]["Literal Minimized POS"])

    """
        Computes logic depth (number of gate levels) from inputs to each output
    """
    def getLogicDepth(self) -> dict[str, int]:
        depth = {inp: 0 for inp in self.inputs}
        # In-degree based DAG traversal
        in_degree = {n.uniqueID: len([i for i in n.inputs if i not in self.inputs]) for n in self.nodes}
        ready = deque([n for n in self.nodes if in_degree[n.uniqueID] == 0])

        while ready:
            curr = ready.popleft()
            curr_depth = max([depth.get(i, 0) for i in curr.inputs], default=0) + 1
            depth[curr.output] = max(depth.get(curr.output, 0), curr_depth)

            for nextNode in curr.nextNodes:
                in_degree[nextNode.uniqueID] -= 1
                if in_degree[nextNode.uniqueID] == 0:
                    ready.append(nextNode)

        return {out: depth.get(out, 0) for out in self.outputs}

    """
        Formats algebraic SOP expression from binary minterm list
    """
    def _formatSOPExpr(self, terms: list[str]) -> str:
        if not terms:
            return "0"
        if any(all(bit == "-" for bit in m) for m in terms):
            return "1"
        if len(terms) == (1 << len(self.inputs)):
            return "1"
        prod_list = []
        for m in terms:
            literals = []
            for var, bit in zip(self.inputs, m):
                if bit == "1":
                    literals.append(var)
                elif bit == "0":
                    literals.append(f"{var}'")
            prod_list.append("".join(literals) if literals else "1")
        return " + ".join(prod_list)

    """
        Formats algebraic POS expression from binary maxterm list
    """
    def _formatPOSExpr(self, terms: list[str]) -> str:
        if not terms:
            return "1"
        if any(all(bit == "-" for bit in m) for m in terms):
            return "0"
        if len(terms) == (1 << len(self.inputs)):
            return "0"
        sum_list = []
        for m in terms:
            literals = []
            for var, bit in zip(self.inputs, m):
                if bit == "0":
                    literals.append(var)
                elif bit == "1":
                    literals.append(f"{var}'")
            sum_list.append(f"({' + '.join(literals)})")
        return "".join(sum_list)

    """
        Formats and returns string of all reported metrics
    """
    def formatMetrics(self) -> str:
        depths = self.getLogicDepth()
        bitWidth = len(self.inputs)
        allInputComb = [f"{i:0{bitWidth}b}" for i in range(1 << bitWidth)]

        lines = []
        lines.append("=" * 70)
        lines.append("LOGIC SYNTHESIS REPORT")
        lines.append(f"Inputs:  {', '.join(self.inputs)}")
        lines.append(f"Outputs: {', '.join(self.outputs)}")
        lines.append("=" * 70)

        for out in self.outputs:
            m = self.metrics[out]
            lines.append(f"\n--- Output: {out} ---")
            lines.append(f"1.  Canonical SOP:              {self._formatSOPExpr(m['Canonical SOP'])}")
            lines.append(f"    Minterms (binary):          {m['Canonical SOP']}")
            lines.append(f"2.  Canonical POS:              {self._formatPOSExpr(m['Canonical POS'])}")
            lines.append(f"    Maxterms (binary):          {m['Canonical POS']}")
            lines.append(f"3.  Inverse Canonical SOP:      {self._formatSOPExpr(m['Inverse Canonical SOP'])}")
            lines.append(f"    Minterms (binary):          {m['Inverse Canonical SOP']}")
            lines.append(f"4.  Inverse Canonical POS:      {self._formatPOSExpr(m['Inverse Canonical POS'])}")
            lines.append(f"    Maxterms (binary):          {m['Inverse Canonical POS']}")
            lines.append(f"5.  Literal Minimized SOP:      {self._formatSOPExpr(m['Literal Minimized SOP'])}")
            lines.append(f"    Literals saved vs canonical: {m['SOP Literals Saved']}")
            lines.append(f"6.  Literal Minimized POS:      {self._formatPOSExpr(m['Literal Minimized POS'])}")
            lines.append(f"    Literals saved vs canonical: {m['POS Literals Saved']}")
            lines.append(f"7.  Prime Implicants:           {len(m['Prime Implicants'])}")
            lines.append(f"8.  Essential Prime Implicants: {len(m['Essential Prime Implicants'])}")
            lines.append(f"9.  ON-Set Minterms (Sigma m):  {m['ON-Set Minterms']}")
            lines.append(f"10. OFF-Set Maxterms (Pi M):    {m['OFF-Set Maxterms']}")
            lines.append(f"11. Custom Command #1 (Delay):  Logic depth = {depths.get(out, 0)} levels")

        # Custom Command #2: Truth Table
        lines.append("\n12. Custom Command #2 (Truth Table Exporter):")
        header = f"    {' '.join(self.inputs)} | {' '.join(self.outputs)}"
        lines.append(header)
        lines.append("    " + "-" * len(header.strip()))
        for inp in allInputComb:
            self.eval(inp)
            out_vals = " ".join([self.varList.get(o, "0") for o in self.outputs])
            inp_vals = " ".join(list(inp))
            lines.append(f"    {inp_vals} | {out_vals}")

        return "\n".join(lines) + "\n"

# Node contains phi(.) or I/O, which is logical function (in our case, SOP) 
# An "input function" is just phi(x) = x.. simple! Minterms would be "1" I suppose
# Since we're doing a BFS, all nodes previously should be resolved, meaning phi 
# must be resolvable by the time it is reached 
class Node(object):
    id_available = 0
    def __init__(self, minTerms: set, inputs: list[str], output: str, name=""):
        # contains set of minTerms in ON SET; ex: {"01", "10"} = XOR
        self.minTerms = minTerms

        # list of names of inputs (ORDERING MATTERS --> used to figure out MSB)
        self.inputs = inputs

        # name of output 
        self.output = output

        # for book-keeping when doing BFS
        if name == "":
            self.uniqueID = f"phi{Node.id_available}"
            Node.id_available += 1
        else:
            self.uniqueID = name

        self.nextNodes = []

    def eval(self, inputLiteral: str) -> str:
        if inputLiteral in self.minTerms:
            return "1"
        for m in self.minTerms:
            if len(m) == len(inputLiteral) and all(c == '-' or c == b for c, b in zip(m, inputLiteral)):
                return "1"
        return "0"

if __name__ == "__main__":
    print("Test with half adder DAG: ")
    hadderDAG = TopCktDAG(["a", "b"], ["sum", "cout", "coutNot"])
    xorGate = Node({"01", "10"}, ["a", "b"], "sum")
    andGate = Node({"11"}, ["a", "b"], "cout")
    invGate = Node({"0"}, ["cout"], "coutNot")
    andGate.nextNodes.append(invGate)
    hadderDAG.initNodes = [xorGate, andGate]
    hadderDAG.nodes = [xorGate, andGate, invGate]
    hadderDAG.evalMetrics()
    print(hadderDAG.metrics["coutNot"])
    print("\nMetrics Report Preview:")
    print(hadderDAG.formatMetrics())
