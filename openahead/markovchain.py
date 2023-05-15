import re
import sys

from collections import deque, Counter
from itertools import islice

from pathlib import Path


regex = re.compile(r'openat\(AT_FDCWD, "(/[^"]+)",')


def read_path_from_file(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            match = regex.search(line)
            if match:
                yield Path(match.group(1)).as_posix()


def read_path_from_stdin():
    for line in sys.stdin:
        match = regex.search(line)
        if match:
            yield Path(match.group(1)).as_posix()


def read_stdin():
    for line in sys.stdin:
        yield line.strip()


class MarkovChain:
    def __init__(self, order=1):
        self.order = order
        self.transitions = {}
        self.context = deque(maxlen=order+1)

    def update(self, token):        
        self.context.append(token)
        if len(self.context) > self.order:
            _context = tuple(islice(self.context, 0, self.order))

            if _context not in self.transitions:
                self.transitions[_context] = Counter()

            self.transitions[_context][token] += 1
            self.context.popleft()

    def predict_all(self, context):
        if context in self.transitions:
            tokens, counts = zip(*self.transitions[context].items())
            total_count = sum(counts)
            probabilities = [count / total_count for count in counts]
            return tokens, probabilities

        return [], []
    
    def get_next(self, context):
        try:
            total_count = sum(self.transitions[context].values())
            most_common = self.transitions[context].most_common(1)
            
            if context in self.transitions:
                path = most_common[0][0]
                prob = most_common[0][1] / total_count
                return path, prob
        except KeyError:    # context가 없을 경우
            return None, None

    def predict(self, data, n=1, update=False, verbose=False, full_context=False):
        assert(n > 0)

        predictions = []

        if full_context:
            assert(isinstance(data, tuple))
            assert(len(data) == self.order)
            copy_context = deque(data)
            if update:
                # ignore warning
                print('update is ignored when full_context is True')
        else:
            copy_context = deque(self.context)

            if update:
                self.update(data)
            else:
                copy_context.popleft()
                copy_context.append(data)

            if len(self.context) != self.order:
                return None

        if verbose:
            print(f"Predict: {tuple(copy_context)}")
            print(f"Predicting next {n} tokens...")
            print()

        for i in range(n):
            next_token, prob = self.get_next(tuple(copy_context))
            
            if verbose:
                print(f"  Context: {tuple(copy_context)}")
                print(f"  Next token: {next_token}")
                print(f"  Probability: {prob}")
                print()

            if next_token is not None:
                predictions.append(next_token)
                copy_context.popleft()
                copy_context.append(next_token)
        
        return predictions



if __name__ == "__main__":
    mc = MarkovChain(order=2)

    for data in read_stdin():
        print(f'predict: {data} -> {mc.predict(data, n=3, update=True, verbose=True)}')