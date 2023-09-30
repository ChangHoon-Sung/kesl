class Node:
    def __init__(self):
        self.weight = 1
        self.edges = dict()

    def get(self, c):
        for e in self.edges:
            if e == c:
                return self.edges[e]
        return None

    def print(self):
        for c in self.edges:
            print(c, end=' ')
            print(round(self.edges[c].weight / self.weight, 2), end=' ')
        if len(self.edges) != 0:
            print()
        for c in self.edges:
            self.edges[c].print()


def buildTree(string):
    root = Node()
    root.weight = 0
    node = root
    for c in string:
        child = node.get(c)
        if child is not None:
            node = child
            node.weight += 1
        else:
            if len(node.edges) == 0 and node.weight >= 1:
                node.edges[c] = Node()
                node.edges['X'] = Node()
            else:
                node.edges[c] = Node()
            root.weight += 1
            node = root
    root.print()


if __name__ == "__main__":
    str = input("문자열을 입력하세요: ")
    buildTree(str)
