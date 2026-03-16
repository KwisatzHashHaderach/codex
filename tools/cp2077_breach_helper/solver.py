from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Step:
    row: int
    col: int
    token: str


@dataclass(frozen=True)
class SolveResult:
    path: list[Step]
    matched_sequences: list[int]


class BreachSolver:
    """Solver for Cyberpunk 2077 Breach Protocol path constraints."""

    def __init__(self, matrix: list[list[str]], sequences: list[list[str]], buffer_size: int):
        self.matrix = [[token.upper() for token in row] for row in matrix]
        self.sequences = [[token.upper() for token in seq] for seq in sequences if seq]
        self.buffer_size = buffer_size
        self.height = len(self.matrix)
        self.width = len(self.matrix[0]) if self.matrix else 0

    def solve(self) -> SolveResult:
        best_path: list[Step] = []
        best_matched: list[int] = []

        if not self.matrix or self.buffer_size <= 0:
            return SolveResult(path=[], matched_sequences=[])

        for col in range(self.width):
            start = Step(0, col, self.matrix[0][col])
            self._dfs(
                path=[start],
                used={(0, col)},
                choose_row=False,
                best=lambda p, m: self._update_best(p, m, best_path, best_matched),
            )

        return SolveResult(path=best_path.copy(), matched_sequences=best_matched.copy())

    def _update_best(
        self,
        path: list[Step],
        matched_sequences: list[int],
        best_path: list[Step],
        best_matched: list[int],
    ) -> None:
        candidate_score = (len(matched_sequences), len(path))
        best_score = (len(best_matched), len(best_path))
        if candidate_score > best_score:
            best_path.clear()
            best_path.extend(path)
            best_matched.clear()
            best_matched.extend(matched_sequences)

    def _dfs(self, path: list[Step], used: set[tuple[int, int]], choose_row: bool, best) -> None:
        matched = self._matched_sequences([step.token for step in path])
        best(path, matched)

        if len(path) >= self.buffer_size:
            return

        last = path[-1]
        candidates: list[tuple[int, int]] = []
        if choose_row:
            row = last.row
            for col in range(self.width):
                if (row, col) not in used:
                    candidates.append((row, col))
        else:
            col = last.col
            for row in range(self.height):
                if (row, col) not in used:
                    candidates.append((row, col))

        for row, col in candidates:
            path.append(Step(row, col, self.matrix[row][col]))
            used.add((row, col))
            self._dfs(path, used, not choose_row, best)
            used.remove((row, col))
            path.pop()

    def _matched_sequences(self, tokens: list[str]) -> list[int]:
        matched: list[int] = []
        for index, sequence in enumerate(self.sequences):
            if self._contains_subsequence(tokens, sequence):
                matched.append(index)
        return matched

    @staticmethod
    def _contains_subsequence(tokens: list[str], sequence: list[str]) -> bool:
        if len(sequence) > len(tokens):
            return False
        for start in range(len(tokens) - len(sequence) + 1):
            if tokens[start : start + len(sequence)] == sequence:
                return True
        return False
