from pathlib import Path
from enum import Enum

# set of supported commands
COMMANDS = {".model", ".names", ".end", ".subckt", ".inputs", ".outputs", "#"}

# subckt = .subckt command
class SubCircuit(object):
    def __init__(self, modelName: str, connections: list[str]):
        self.modelName = modelName
        self.connections = connections

# model = .model command -> .end
class Model(object):
    def __init__(self):
        self.inputs = []
        self.outputs = []
        self.name = ""
        self.gates = []
        self.subModels = []

    """
        To-Do: Have a fcn that takes in subModels and "expands them out"
        into proper gates so that everything is connected properly in one top-level model

        By the end, subModels should be empty and everything should be described in gates
    """
    def flattenModel(self, modelList: dict) -> None:
        if not self.subModels:
            return

        flattenedGates = []
        instanceCount = 0

        for sub in self.subModels:
            if sub.modelName not in modelList:
                raise ValueError(f"Subcircuit model '{sub.modelName}' not found.")
            subModel = modelList[sub.modelName]
            # recursively flatten submodel if it has nested subcircuits
            subModel.flattenModel(modelList)

            # Map formal pins to actual signal names
            wireMap = {}
            if sub.connections and "=" in sub.connections[0]:
                for conn in sub.connections:
                    formal, actual = conn.split("=", 1)
                    wireMap[formal] = actual
            else:
                formalPins = subModel.inputs + subModel.outputs
                for formal, actual in zip(formalPins, sub.connections):
                    wireMap[formal] = actual

            # Expand gates from submodel with mapped wire names
            for g in subModel.gates:
                newGate = Gate()
                newGate.minTerms = set(g.minTerms)
                for inp in g.inputs:
                    newGate.inputs.append(wireMap.get(inp, f"{sub.modelName}_{instanceCount}_{inp}"))
                for out in g.outputs:
                    newGate.outputs.append(wireMap.get(out, f"{sub.modelName}_{instanceCount}_{out}"))
                flattenedGates.append(newGate)

            instanceCount += 1

        self.gates = flattenedGates + self.gates
        self.subModels = []

# gate = .names command
class Gate(object):
    id_available = 0 # unique id for each gate
    def __init__(self):
        self.inputs = []
        self.outputs = []
        # should be a set of minterms "00", "01", etc. order matters once again
        self.minTerms = set()
        self.id = f"phi{Gate.id_available}"
        Gate.id_available += 1 # increment for every instantiated gate object

def expandDontCares(term: str) -> list[str]:
    if "-" not in term:
        return [term]
    pos = term.index("-")
    return expandDontCares(term[:pos] + "0" + term[pos + 1:]) + expandDontCares(term[:pos] + "1" + term[pos + 1:])

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
            line = line.rstrip("\n")
            if "#" in line:
                line = line[:line.index("#")]
            tokenAtLine = line.split()
            if not tokenAtLine:
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
    modelList = {}
    currentModel = ""
    definedModelsWithEnd = set()

    for c in command_list:
        if c[0] not in COMMANDS:
            raise ValueError(f"Invalid blif command: {c[0]}")
        if c[0] == ".model":
            modelName = c[1]
            if modelName in modelList:
                raise ValueError(f"Duplicate model name: {modelName}")
            modelList[modelName] = Model()
            modelList[modelName].name = modelName
            currentModel = modelName
        elif c[0] == ".inputs":
            if not currentModel:
                raise ValueError(".inputs defined outside of .model block.")
            for inp in c[1:]:
                if inp in modelList[currentModel].inputs or inp in modelList[currentModel].outputs:
                    raise ValueError(f"Duplicate I/O pin name: {inp}")
                modelList[currentModel].inputs.append(inp)
        elif c[0] == ".outputs":
            if not currentModel:
                raise ValueError(".outputs defined outside of .model block.")
            for out in c[1:]:
                if out in modelList[currentModel].inputs or out in modelList[currentModel].outputs:
                    raise ValueError(f"Duplicate I/O pin name: {out}")
                modelList[currentModel].outputs.append(out)
        elif c[0] == ".subckt":
            if not currentModel:
                raise ValueError(".subckt defined outside of .model block.")
            modelList[currentModel].subModels.append(SubCircuit(c[1], c[2:]))
        elif c[0] == ".names":
            c_args = c[1:]
            idx = next((i for i, s in enumerate(c_args) if s and (s[0].isdigit() or s[0] == "-")), len(c_args))
            inputOutputPins = c_args[:idx]

            # If no model is defined, default to first .names
            if not currentModel:
                currentModel = inputOutputPins[-1]
                modelList[currentModel] = Model()
                modelList[currentModel].name = currentModel
                modelList[currentModel].inputs = inputOutputPins[:-1]
                modelList[currentModel].outputs = [inputOutputPins[-1]]

            rawTerms = c_args[idx::2]
            minTerms = set()
            for term in rawTerms:
                minTerms.update(expandDontCares(term))

            tmpGate = Gate()
            tmpGate.inputs = inputOutputPins[:-1]
            tmpGate.outputs.append(inputOutputPins[-1])
            tmpGate.minTerms = minTerms
            modelList[currentModel].gates.append(tmpGate)
        elif c[0] == ".end":
            if currentModel:
                if not modelList[currentModel].inputs or not modelList[currentModel].outputs:
                    raise ValueError(f"Model '{currentModel}' must define both .inputs and .outputs.")
                definedModelsWithEnd.add(currentModel)
                currentModel = ""

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
    testFile = Path(__file__).resolve().parent.parent.parent / "test_BLIF" / "halfAdder.blif"
    com = getCommandList(testFile)
    mdls = modelListConstructor(com)
    printModelList(mdls)
