import win32file
import struct


class SHTreader:
    def __init__(self, path=None, mode='r'):
        self.path = ""
        self.file = None
        self.version = None
        self.mode = mode
        self.count = 0
        if path:
            self.path = path
            self.open_file()
            self.parse()

    def parse(self):
        self.get_version()
        self.file.read(1)
        count = struct.unpack("<i", self.file.read(4))[0]
        print(count)
        self.count = count

    def open_file(self):
        if self.path and self.mode == 'r':
            self.file = open(self.path, 'rb')

    def get_version(self):
        if self.version:
            return self.version
        if self.file:
            base = b"ANALIZER"
            s = self.file.read(len(base))
            print(s)
            if s != base:
                print("Wooops, invalid file beginning")
                return None
            version = self.file.read(3)
            version = version.decode('ascii')

            self.version = int(version[-1])
            print(version)
            if self.version not in range(0, 3):
                print("Wooops, invalid file version ".format(version))
                self.version = None
                return None
            print("opened file with version " + version)
            return self.version
        else:
            print("Wooops, invalid file handle")
        return None

    def read_oscillogram(self):
        size = struct.unpack("i", self.file.read(4))[0]
        print(size)
        data = self.file.read(size)
        self.decompress_oscillogram(data, size)

    def decompress_oscillogram(self, data, size):
        self.decompress_huffman(data, size)
        return
        #H1=DecompressHoffman(H,Size,&Size1);

    def decompress_huffman(self, data, size):
        graph = self.create_graph(data)
        print(list(zip(graph, range(256))))
        return

    def create_graph(self, data):
        mask = [512 for i in range(256)]
        graph = [[0, 1] for i in range(256)]
        v = 0
        prev = 0
        for i in range(256):
            if data[i] != 255:
                prev = i
                v = data[i]
                print(prev, v)
                while True:
                    if mask[v] == 512:
                        mask[v] = prev
                    graph[v][int(mask[v] != prev)] = prev
                    prev = v + 256
                    v = data[prev]
                    if v == data[prev]:
                        break
        graph[255] = graph[prev-255]
        return graph