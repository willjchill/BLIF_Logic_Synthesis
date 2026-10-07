from pathlib import Path
from enum import Enum
import logicDAG as ld

# set of supported commands
COMMANDS = {".model", ".names", ".end", ".subckt", ".inputs", ".outputs", "#"}

# model = .model command -> .end
class Model(object):
    def __init__(self):
        self.inputs = []
        self.outputs = []
        self.name = ""
        self.gates = []

# gate = .names command
class Gate(object):
    def __init__(self):
        self.inputs = []
        self.outputs = []
        # should be a set of minterms "00", "01", etc. order matters once again
        self.minTerms = set()

"""
    If you have a blif file with commands,
    it will returns a list of lists such that it tells you the command and all of its parameters.

    Example:
    [[.model, top], [.inputs, a, b], [.outputs, sum, cout], [.names, a, b, cout, 11, 1], [.end]]
"""
def getCommandList(filePath: Path) -> list[list[str]]:
    with filePath.open("r", encoding="utf-8") as file:
        token_list = []

        for line in file:
            # get list of tokens
            line = line.rstrip("\n")
            tokenAtLine = line.split()
            if tokenAtLine == [] or tokenAtLine[0] == "#":
                continue
            token_list.extend(tokenAtLine)

        # Find all indices where a string starts with ".", e.g. a command
        dots = [i for i, s in enumerate(token_list) if s.startswith(".")]
        # Slice the list from one dot index to the next (and to the end for the last slice)
        command_list = [token_list[i:j] for i, j in zip(dots, dots[1:] + [len(token_list)])]
        return command_list

"""
    Based on a command_list, it will construct a data structure of models that contain gates/submodels

    Returns a dictionary of each of the models that are called within the BLIF file
"""
def modelListConstructor(command_list: list[list[str]]):
    # now.. we need to convert this from command_list --> DAG
    # let's try it for one model, assuming no subckt for simplicity
    # create dictionary of models
    modelList = {}
    currentModel = ""
    for c in command_list:
        if c[0] not in COMMANDS:
            raise ValueError("Invalid blif code.")
        if c[0] == ".model":
            modelList[c[1]] = Model()
            modelList[c[1]].name = c[1] 
            currentModel = c[1]
        elif c[0] == ".inputs":
            for inp in c[1:]:
                modelList[currentModel].inputs.append(inp)
        elif c[0] == ".outputs":
            for out in c[1:]:
                modelList[currentModel].outputs.append(out)
        elif c[0] == ".names":
            # removing command and only analyzing everything after
            c = c[1:]
            # finding idx when digits first occur
            idx = next((i for i, s in enumerate(c) if s and s[0].isdigit()), len(c))
            inputOutputPins = c[:idx]
            minTerms = set(c[idx::2])
            tmpGate = Gate()
            tmpGate.inputs = inputOutputPins[:-1]
            tmpGate.outputs.append(inputOutputPins[-1])
            tmpGate.minTerms = minTerms
            modelList[currentModel].gates.append(tmpGate)
        elif c[0] == ".end":
            break
    return modelList 

"""
    Debug print function that helps visualize what has been identified in BLIF file
"""
def printModelList(modelList) -> None:
    print("Module & Gates")
    for m in modelList:
        print(f"Model {m}:") 
        print("All the gates: ")
        for g in modelList[m].gates: 
            print(f"Gate {g.inputs} , {g.outputs}, {g.minTerms}")

if __name__ == "__main__":
    testFile = Path("../../test_BLIF/halfAdder.blif")
    com = getCommandList(testFile)
    mdls = modelListConstructor(com)
    printModelList(mdls)
