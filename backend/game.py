import random
import time
from typing import Optional

ROWS = 16
COLS = 30
MINES = 99


def get_neighbors(r: int, c: int) -> list[tuple[int, int]]:
    return [
        (r + dr, c + dc)
        for dr in (-1, 0, 1)
        for dc in (-1, 0, 1)
        if (dr or dc) and 0 <= r + dr < ROWS and 0 <= c + dc < COLS
    ]


class Cell:
    __slots__ = ("mine", "revealed", "flagged", "n")

    def __init__(self):
        self.mine: bool = False
        self.revealed: bool = False
        self.flagged: bool = False
        self.n: int = 0  # adjacent mine count


class Game:
    def __init__(self):
        self.reset()

    def reset(self):
        self.board: list[list[Cell]] = [
            [Cell() for _ in range(COLS)] for _ in range(ROWS)
        ]
        self.status: str = "idle"  # idle | playing | won | lost
        self.start_time: Optional[float] = None
        self._elapsed: int = 0

    # ── Mine placement ─────────────────────────────────────────────────────

    def _place_mines(self, fr: int, fc: int):
        safe = {(fr, fc)} | set(get_neighbors(fr, fc))
        candidates = [
            (r, c)
            for r in range(ROWS)
            for c in range(COLS)
            if (r, c) not in safe
        ]
        for r, c in random.sample(candidates, MINES):
            self.board[r][c].mine = True

        for r in range(ROWS):
            for c in range(COLS):
                if not self.board[r][c].mine:
                    self.board[r][c].n = sum(
                        1 for nr, nc in get_neighbors(r, c) if self.board[nr][nc].mine
                    )

    # ── Actions ────────────────────────────────────────────────────────────

    def reveal(self, r: int, c: int) -> str:
        """Returns: 'noop' | 'continue' | 'won' | 'lost'"""
        cell = self.board[r][c]
        if cell.revealed or cell.flagged or self.status not in ("idle", "playing"):
            return "noop"

        if self.status == "idle":
            self._place_mines(r, c)
            self.status = "playing"
            self.start_time = time.time()

        # BFS flood fill
        stack = [(r, c)]
        visited: set[tuple[int, int]] = set()
        hit_mine = False

        while stack:
            cr, cc = stack.pop()
            if (cr, cc) in visited:
                continue
            visited.add((cr, cc))
            cur = self.board[cr][cc]
            if cur.revealed or cur.flagged:
                continue
            cur.revealed = True
            if cur.mine:
                hit_mine = True
                break
            if cur.n == 0:
                stack.extend(get_neighbors(cr, cc))

        if hit_mine:
            for row in self.board:
                for cell in row:
                    if cell.mine:
                        cell.revealed = True
            self.status = "lost"
            self._elapsed = int(time.time() - self.start_time)
            return "lost"

        if self._check_win():
            # Auto-flag remaining mines
            for row in self.board:
                for cell in row:
                    if cell.mine and not cell.flagged:
                        cell.flagged = True
            self.status = "won"
            self._elapsed = int(time.time() - self.start_time)
            return "won"

        return "continue"

    def chord(self, r: int, c: int) -> str:
        """
        Chord click: if a revealed numbered cell has exactly as many flagged
        neighbours as its number, reveal all remaining unflagged neighbours.
        Returns same codes as reveal(): 'noop' | 'continue' | 'won' | 'lost'
        """
        cell = self.board[r][c]
        if not cell.revealed or cell.n == 0 or self.status != "playing":
            return "noop"
        ns = get_neighbors(r, c)
        n_flagged = sum(1 for nr, nc in ns if self.board[nr][nc].flagged)
        if n_flagged != cell.n:
            return "noop"
        # Reveal every unflagged unrevealed neighbour
        result = "continue"
        for nr, nc in ns:
            nb = self.board[nr][nc]
            if not nb.revealed and not nb.flagged:
                res = self.reveal(nr, nc)
                if res == "lost":
                    return "lost"
                if res == "won":
                    result = "won"
        return result

    def flag(self, r: int, c: int) -> bool:
        cell = self.board[r][c]
        if cell.revealed or self.status not in ("idle", "playing"):
            return False
        cell.flagged = not cell.flagged
        return True

    # ── Helpers ────────────────────────────────────────────────────────────

    def _check_win(self) -> bool:
        return all(cell.mine or cell.revealed for row in self.board for cell in row)

    @property
    def mines_left(self) -> int:
        return MINES - sum(cell.flagged for row in self.board for cell in row)

    @property
    def elapsed(self) -> int:
        if self.start_time and self.status == "playing":
            return int(time.time() - self.start_time)
        return self._elapsed

    def to_dict(self) -> dict:
        show_mines = self.status in ("won", "lost")
        return {
            "status": self.status,
            "elapsed": self.elapsed,
            "mines_left": self.mines_left,
            "board": [
                [
                    {
                        "revealed": cell.revealed,
                        "flagged": cell.flagged,
                        "mine": cell.mine if show_mines else False,
                        "n": cell.n if cell.revealed else 0,
                    }
                    for cell in row
                ]
                for row in self.board
            ],
        }
