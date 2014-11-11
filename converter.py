import os
import shutil


class Shot:
    def __init__(self, file):
        self.file = file.split('/')[-1].split(".")[:-1]
        self.result = "".join(["files/"] + file.split('/')[-1].split(".")[:-1]+[".csv"])
        os.system(r'test.exe "{0}" "{1}"'.format(file, self.result))
        with open(self.result, "rt") as inp:
            lines = inp.readlines()
        self.length = int(lines[0])
        self.diagrams = []
        j = 1
        for i in range(self.length):
            diagram = []
            diagram.append(lines[j:j+3])
            j += 3
            k = int(lines[j])
            j += 1
            x = []
            y = []
            for l in range(k):
                x0, y0 = lines[j].split()
                j += 1
                x.append(float(x0))
                y.append(float(y0))
            diagram.append(x)
            diagram.append(y)
            self.diagrams.append(Diagram(diagram))

    def get_diagram_names(self):
        return [x.name for x in self.diagrams]

    def get_diagram(self, n):
        return self.diagrams[n]



class Diagram:
    def __init__(self, data=None):
        self.x = []
        self.y = []
        self.name = ''
        self.comment = ''
        self.unit = ''
        if data:
            self.x = data[1]
            self.y = data[2]
            self.name = data[0][0]
            self.comment = data[0][1]
            self.unit = data[0][2]