import unittest

from solver import BreachSolver


class BreachSolverTests(unittest.TestCase):
    def test_finds_path_that_matches_two_sequences(self) -> None:
        matrix = [
            ["1C", "55", "E9", "7A"],
            ["55", "1C", "7A", "BD"],
            ["BD", "E9", "55", "1C"],
            ["7A", "55", "1C", "E9"],
        ]
        sequences = [["1C", "55"], ["55", "1C", "7A"]]

        result = BreachSolver(matrix=matrix, sequences=sequences, buffer_size=5).solve()

        self.assertEqual(result.matched_sequences, [0, 1])
        self.assertEqual(len(result.path), 5)
        self.assertEqual(result.path[0].row, 0)

    def test_empty_matrix(self) -> None:
        result = BreachSolver(matrix=[], sequences=[["1C"]], buffer_size=4).solve()
        self.assertEqual(result.path, [])
        self.assertEqual(result.matched_sequences, [])


if __name__ == "__main__":
    unittest.main()
