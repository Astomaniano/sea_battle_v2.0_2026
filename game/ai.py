import random

from .board import Board
from .ui import GRID_SIZE


class Player:
    def __init__(self):
        self.board = Board()


class AIPlayer(Player):
    def __init__(self):
        super().__init__()
        self.mode = "search"
        self.target_queue = []
        self.current_hits = []

    def choose_shot(self, enemy_board):
        if self.mode == "target":
            while self.target_queue and enemy_board.shots[self.target_queue[0][1]][self.target_queue[0][0]] != 0:
                self.target_queue.pop(0)
            if not self.target_queue:
                self.mode = "search"
                self.current_hits = []

        if self.mode == "target" and self.target_queue:
            return self.target_queue.pop(0)

        candidates = [(x, y) for y in range(GRID_SIZE) for x in range(GRID_SIZE) if enemy_board.shots[y][x] == 0]
        if not candidates:
            return None
        return random.choice(candidates)

    def process_result(self, coord, result, enemy_board):
        if result == "hit":
            self.mode = "target"
            self.current_hits.append(coord)
            self._update_targets(enemy_board)
        elif result == "sunk":
            self.mode = "search"
            self.target_queue = []
            self.current_hits = []

    def _update_targets(self, enemy_board):
        if not self.current_hits:
            return

        if len(self.current_hits) == 1:
            x, y = self.current_hits[0]
            neighbors = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
            for nx, ny in neighbors:
                if enemy_board.in_bounds(nx, ny) and enemy_board.shots[ny][nx] == 0:
                    if (nx, ny) not in self.target_queue:
                        self.target_queue.append((nx, ny))
            return

        xs = {c[0] for c in self.current_hits}
        ys = {c[1] for c in self.current_hits}
        if len(xs) == 1:
            x = next(iter(xs))
            min_y = min(ys)
            max_y = max(ys)
            for ny in [min_y - 1, max_y + 1]:
                if enemy_board.in_bounds(x, ny) and enemy_board.shots[ny][x] == 0:
                    if (x, ny) not in self.target_queue:
                        self.target_queue.append((x, ny))
        elif len(ys) == 1:
            y = next(iter(ys))
            min_x = min(xs)
            max_x = max(xs)
            for nx in [min_x - 1, max_x + 1]:
                if enemy_board.in_bounds(nx, y) and enemy_board.shots[y][nx] == 0:
                    if (nx, y) not in self.target_queue:
                        self.target_queue.append((nx, y))
