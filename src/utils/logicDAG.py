from collections import deque
import blifParser
from pathlib import Path

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
                                 "OFF-Set Minterms": 0
                                 } for output in self.outputs}
 
    """
        inputLiteral = sets all inputs in order, last in list is MSB
        ex: self.inputs = ["a", "b"]
        if I want a=0, b=1 --> "10"

        just initializes the var list for you
        contains a dictionary of what all the var are evaluated to
    """
    def eval(self, inputLiteral: str) -> None:
        for i in range(len(inputLiteral)):
            self.varList[self.inputs[i]] = inputLiteral[i]

        for n in self.initNodes:
            self.q.append(n)
        
        # BFS algorithm to evaluate all the intermediates nodes from inputs -> outputs
        while self.q:
            currentNode = self.q.popleft()
            tmpInput = "".join([self.varList[c] for c in currentNode.inputs])
            self.varList[currentNode.output] = currentNode.eval(tmpInput)
            for n in currentNode.nextNodes:
                self.q.append(n)

    """
        converts models/gates notation from BLIF format --> our std DAG structure
        should set all the appropiate attributes in this DAG 
    """
    def model2DAG(self, top_model: blifParser.Model) -> None:
        # assuming it only has gates for now... need to keep things simple
        self.inputs = top_model.inputs
        self.outputs = top_model.outputs
        # idk for now (a bit stuck)

        

    """
        Updates dictionary with all required metrics, saving it in metrics attribute 
    """
    def evalMetrics(self) -> None:
        # init metric dictionary for all top-level outputs

        bitWidth = len(self.inputs)
        allInputComb = [f"{i:0{bitWidth}b}" for i in range(1 << bitWidth)]
        # 1: canonical SOP
        for output in self.outputs:
            for input in allInputComb:
                self.eval(input)
                if self.varList[output] == "1":
                    self.metrics[output]["Canonical SOP"].append(input)
                    self.metrics[output]["Inverse Canonical POS"].append(input)
                else:
                    self.metrics[output]["Canonical POS"].append(input)
                    self.metrics[output]["Inverse Canonical SOP"].append(input)
            self.metrics[output]["ON-Set Minterms"] = len(self.metrics[output]["Canonical SOP"])
            self.metrics[output]["OFF-Set Minterms"] = len(self.metrics[output]["Canonical POS"])

# Node contains phi(.), which is logical function (in our case, SOP) 
# Since we're doing a BFS, all nodes previously should be resolved, meaning phi 
# must be resolvable by the time it is reached 
class Node(object):
    def __init__(self, minTerms: set, inputs: list[str], output: str):
        # contains set of minTerms in ON SET; ex: {"01", "10"} = XOR
        self.minTerms = minTerms

        # list of names of inputs (ORDERING MATTERS --> used to figure out MSB)
        self.inputs = inputs

        # name of output 
        self.output = output

        self.nextNodes = []

    def eval(self, inputLiteral: str) -> str:
        if inputLiteral in self.minTerms:
            return "1"
        return "0"

if __name__ == "__main__":
    # going to try to use blif parser to construct our DAG 
    testFile = Path("../../test_BLIF/halfAdder.blif")
    com = blifParser.getCommandList(testFile)
    mdls = blifParser.modelListConstructor(com)
    blifParser.printModelList(mdls)
    # need model2dag function
    # getting first model as iterated in dictionary
    # hadderDAG.model2DAG(mdls[next(iter(mdls))])

    # print("Test with half adder DAG: ")
    # hadderDAG = TopCktDAG(["a", "b"], ["sum", "cout", "coutNot"])
    # xorGate = Node({"01", "10"}, ["a", "b"], "sum")
    # andGate = Node({"11"}, ["a", "b"], "cout")
    # invGate = Node({"0"}, ["cout"], "coutNot")
    # andGate.nextNodes.append(invGate)
    # hadderDAG.initNodes = [xorGate, andGate]
    # # half-adder DAG should be like this:
    # # ab format
    # #testInputs = ["00", "01", "10", "11"]
    # #for i in range(4):
    # #    hadderDAG.eval(testInputs[i])
    # #    print(f"Half adder output for a = {testInputs[i][0]} and b = {testInputs[i][1]}:")
    # #    print(hadderDAG.varList)
    # hadderDAG.evalMetrics()
    # print(hadderDAG.metrics["coutNot"])
