import os
import shutil
import numpy as np

class Shot:
    def __init__(self, file):
        self.file = file.split('/')[-1].split(".")[:-1]
        self.result = "".join(["files/"] + file.split('/')[-1].split(".")[:-1]+[".csv"])
        if not os.path.isfile(self.result):
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
        return [x.name.strip() for x in self.diagrams]

    def get_diagram_for_name(self, name):
        for x in self.diagrams:
            if name in x.name.strip():
                return x

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

    def for_x(self, v):
        if type(v) is list:
            vals = v
        else:
            vals = [v]
        p = np.searchsorted(self.x, vals)
        res = []
        for i in range(len(vals)):
            if vals[i] == self.x[p[i]]:
                res.append(self.y[p[i]])
            else:
                res.append(self.y[p[i]]+ (self.y[p[i]] - self.y[p[i]-1])*((self.x[p[i]]-self.x[p[i]-1])/(vals[i]-self.x[p[i]-1])))

        return res

