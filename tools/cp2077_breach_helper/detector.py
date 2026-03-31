from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import pytesseract

HEX_TOKEN = re.compile(r"\b(?:1C|55|7A|BD|E9|FF)\b", re.IGNORECASE)


@dataclass
class BreachPuzzle:
    matrix: list[list[str]]
    sequences: list[list[str]]
    buffer_size: int


class BreachDetector:
    """Heuristic screenshot parser for the Breach Protocol overlay."""

    def parse_screenshot(self, screenshot_path: str | Path) -> BreachPuzzle | None:
        image = cv2.imread(str(screenshot_path))
        if image is None:
            return None

        if not self._looks_like_breach_screen(image):
            return None

        matrix = self._extract_matrix(image)
        sequences = self._extract_sequences(image)
        buffer_size = max((len(seq) for seq in sequences), default=6)

        if not matrix or not sequences:
            return None

        return BreachPuzzle(matrix=matrix, sequences=sequences, buffer_size=buffer_size)

    def _looks_like_breach_screen(self, image: np.ndarray) -> bool:
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        yellow = cv2.inRange(hsv, (18, 80, 80), (40, 255, 255))
        yellow_ratio = float(np.count_nonzero(yellow)) / yellow.size
        return yellow_ratio > 0.02

    def _extract_matrix(self, image: np.ndarray) -> list[list[str]]:
        h, w = image.shape[:2]
        crop = image[int(h * 0.25) : int(h * 0.8), int(w * 0.08) : int(w * 0.45)]
        text = pytesseract.image_to_string(crop, config="--psm 6")
        tokens = [token.upper() for token in HEX_TOKEN.findall(text)]

        if len(tokens) < 16:
            return []

        edge = int(len(tokens) ** 0.5)
        if edge * edge != len(tokens):
            edge = 6

        matrix: list[list[str]] = []
        index = 0
        for _row in range(edge):
            row: list[str] = []
            for _col in range(edge):
                if index >= len(tokens):
                    break
                row.append(tokens[index])
                index += 1
            if len(row) == edge:
                matrix.append(row)
        return matrix

    def _extract_sequences(self, image: np.ndarray) -> list[list[str]]:
        h, w = image.shape[:2]
        crop = image[int(h * 0.3) : int(h * 0.72), int(w * 0.50) : int(w * 0.9)]
        text = pytesseract.image_to_string(crop, config="--psm 6")

        sequences: list[list[str]] = []
        for line in text.splitlines():
            line_tokens = [token.upper() for token in HEX_TOKEN.findall(line)]
            if len(line_tokens) >= 2:
                sequences.append(line_tokens)

        return sequences[:3]
