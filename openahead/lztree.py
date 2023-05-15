import re, sys
from pathlib import Path


# strace openat 라인에서 경로 찾기
regex = re.compile(r'openat\(AT_FDCWD, "(/[^"]+)",')


# strace log에서 line-by-line으로 POSIX 경로를 찾아 반환하는 제너레이터
def read_path_from_file(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            match = regex.search(line)
            if match:
                yield Path(match.group(1)).as_posix()

def read_strace_from_stdin():
    for line in sys.stdin:
        match = regex.search(line)
        if match:
            yield Path(match.group(1)).as_posix()


class Node:
    def __init__(self, key, height=0):
        self.weight = 1
        self.edges = dict()
        self.key = key
        self.height = height        # 출력 포맷을 위한 optional 속성

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

    # strace pipe 테스트
    # $ strace -e openat -f gimp 2>&1 | python lztree.py
    for data in read_strace_from_stdin():
        data = data.strip()
        child = node.get(data)
        if child is not None:
            node = child
            node.weight += 1
        else:
            node.edges[data] = Node(data, node.height + 1)
            node.edges[data].edges['$'] = Node('$', node.height + 1)    # End of pattern
            
            root.weight += 1
            node = root
    
    # strace log 파일 테스트
    # log_path = Path('../data/GIMP/strace-gimp-filtered.log')
    # for data in read_path_from_file(log_path):
    #     data = data.strip()
    #     child = node.get(data)
    #     if child is not None:
    #         node = child
    #         node.weight += 1
    #     else:
    #         node.edges[data] = Node(data, node.height + 1)
    #         node.edges[data].edges['$'] = Node('$', node.height + 1)    # End of pattern
            
    #         root.weight += 1
    #         node = root
        
    root.print()

    with open('lztree.json', 'w') as f:
        f.write(str(root))


if __name__ == "__main__":
    buildTree()