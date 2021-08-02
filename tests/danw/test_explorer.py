from unittest import TestCase


def all_state(n=4, mf=3):
    queue = [[], [], [], []]
    state = [1] * n

    def inner(idx: int, k: int):
        if k > mf:
            return
        if idx == n:
            queue[k].append(state.copy())
            return
        state[idx] = 0
        inner(idx + 1, k + 1)
        state[idx] = 1
        inner(idx + 1, k)

    inner(0, 0)
    for states in queue:
        for state in states:
            print(state)


class TestExplorer(TestCase):

    def test_all_state(self):
        all_state()
