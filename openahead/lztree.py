import re, sys
from pathlib import Path

regex = re.compile(r'openat\(AT_FDCWD, "(/[^"]+)",')


def read_path_from_file(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            match = regex.search(line)
            if match:
                yield Path(match.group(1)).as_posix()


class Node:
    def __init__(self, key, height=0):
        self.weight = 1
        self.edges = dict()
        self.key = key
        self.height = height

    def get(self, c):
        for e in self.edges:
            if e == c:
                return self.edges[e]
        return None

    def print(self):
        print(f"{' ' * self.height} Node[{self.key}]:", end=" ")
        for c in self.edges:
            print(c, end=' ')
            print(round(self.edges[c].weight / self.weight, 2), end=' ')
        if len(self.edges) != 0:
            print()
        for c in self.edges:
            if len(self.edges[c].edges) > 0:
                self.edges[c].print()
    
    def __repr__(self):
        # return f'key: {self.key} w: {self.weight} edges: {self.edges}'
        return f'{self.edges}'


def buildTree():
    root = Node('root')
    root.weight = 0
    node = root
    prev = None

    for p in sys.stdin:
        p = p.strip()
        child = node.get(p)
        if child is not None:
            node = child
            node.weight += 1
        else:
            node.edges[p] = Node(p, node.height + 1)
            node.edges[p].edges['$'] = Node('$', node.height + 1)    # End of pattern
            
            root.weight += 1
            node = root
        
        # node.print()
    
    # root.print()
    with open('str.json', 'w') as f:
        f.write(str(root))


if __name__ == "__main__":
    buildTree()