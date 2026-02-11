import random

from .ui import GRID_SIZE


class Ship:
    def __init__(self, cells):
        self.cells = cells
        self.hits = set()

    def hit(self, cell):
        self.hits.add(cell)

    def is_sunk(self):
        return len(self.hits) == len(self.cells)


class Board:
    def __init__(self):
        self.grid = [[-1 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.shots = [[0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.ships = []

    def in_bounds(self, x, y):
        return 0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE

    def place_ships_auto(self):
        self.grid = [[-1 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.shots = [[0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.ships = []

        ship_sizes = [4, 3, 3, 2, 2, 2, 1, 1, 1, 1]
        for size in ship_sizes:
            placed = False
            attempts = 0
            while not placed and attempts < 2000:
                attempts += 1
                horizontal = random.choice([True, False])
                if horizontal:
                    x = random.randint(0, GRID_SIZE - size)
                    y = random.randint(0, GRID_SIZE - 1)
                    cells = [(x + i, y) for i in range(size)]
                else:
                    x = random.randint(0, GRID_SIZE - 1)
                    y = random.randint(0, GRID_SIZE - size)
                    cells = [(x, y + i) for i in range(size)]

                if self.can_place(cells):
                    ship = Ship(cells)
                    ship_index = len(self.ships)
                    for cx, cy in cells:
                        self.grid[cy][cx] = ship_index
                    self.ships.append(ship)
                    placed = True
            if not placed:
                self.place_ships_auto()
                return

    def can_place(self, cells):
        for x, y in cells:
            if not self.in_bounds(x, y):
                return False
            if self.grid[y][x] != -1:
                return False
            for nx in range(x - 1, x + 2):
                for ny in range(y - 1, y + 2):
                    if self.in_bounds(nx, ny) and self.grid[ny][nx] != -1:
                        return False
        return True

    def shoot(self, x, y):
        if not self.in_bounds(x, y):
            return "repeat"
        if self.shots[y][x] != 0:
            return "repeat"

        ship_index = self.grid[y][x]
        if ship_index == -1:
            self.shots[y][x] = 1
            return "miss"

        self.shots[y][x] = 2
        ship = self.ships[ship_index]
        ship.hit((x, y))
        if ship.is_sunk():
            self._mark_around_sunk(ship)
            return "sunk"
        return "hit"

    def _mark_around_sunk(self, ship):
        for x, y in ship.cells:
            for nx in range(x - 1, x + 2):
                for ny in range(y - 1, y + 2):
                    if self.in_bounds(nx, ny) and self.shots[ny][nx] == 0:
                        self.shots[ny][nx] = 1

    def all_sunk(self):
        return all(ship.is_sunk() for ship in self.ships)
