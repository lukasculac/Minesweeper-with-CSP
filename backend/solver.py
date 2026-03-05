from game import ROWS, COLS, MINES, Cell, get_neighbors


# ── CSP constraint solver ─────────────────────────────────────────────────────

def csp_solve(board: list[list[Cell]]) -> dict:
    """
    Phase 1 — deterministic rules:
      • If a revealed cell's remaining unrevealed unflagged neighbors equals
        its remaining mine count → flag them all.
      • If remaining mine count is 0 → reveal them all.

    Phase 2 — probabilistic fallback:
      Pick the unrevealed cell with the lowest estimated mine probability.

    Returns:
        {
            "moves": [{"action": "flag"|"reveal", "row": int, "col": int, "prob": float?}],
            "is_guess": bool
        }
    """
    to_flag: set[tuple[int, int]] = set()
    to_reveal: set[tuple[int, int]] = set()

    for r in range(ROWS):
        for c in range(COLS):
            cell = board[r][c]
            if not cell.revealed or cell.n == 0:
                continue
            ns = get_neighbors(r, c)
            unrev = [(nr, nc) for nr, nc in ns if not board[nr][nc].revealed and not board[nr][nc].flagged]
            n_flagged = sum(1 for nr, nc in ns if board[nr][nc].flagged)
            remaining = cell.n - n_flagged

            if remaining < 0:
                continue
            if remaining == 0:
                to_reveal.update(unrev)
            elif remaining == len(unrev):
                to_flag.update(unrev)

    moves: list[dict] = []
    for r, c in to_flag:
        if not board[r][c].flagged:
            moves.append({"action": "flag", "row": r, "col": c})
    for r, c in to_reveal:
        if not board[r][c].revealed and (r, c) not in to_flag:
            moves.append({"action": "reveal", "row": r, "col": c})

    if moves:
        return {"moves": moves, "is_guess": False}

    # ── Probabilistic fallback ────────────────────────────────────────────
    total_flagged = sum(cell.flagged for row in board for cell in row)
    all_unrev = [
        (r, c)
        for r in range(ROWS)
        for c in range(COLS)
        if not board[r][c].revealed and not board[r][c].flagged
    ]

    if not all_unrev:
        return {"moves": [], "is_guess": False}

    global_p = (MINES - total_flagged) / len(all_unrev)
    prob_map: dict[tuple[int, int], float] = {}

    for r in range(ROWS):
        for c in range(COLS):
            cell = board[r][c]
            if not cell.revealed or cell.n == 0:
                continue
            ns = get_neighbors(r, c)
            unrev = [(nr, nc) for nr, nc in ns if not board[nr][nc].revealed and not board[nr][nc].flagged]
            n_flagged = sum(1 for nr, nc in ns if board[nr][nc].flagged)
            remaining = cell.n - n_flagged
            if unrev and remaining >= 0:
                p = remaining / len(unrev)
                for pos in unrev:
                    prob_map[pos] = max(prob_map.get(pos, 0.0), p)

    best = min(all_unrev, key=lambda pos: prob_map.get(pos, global_p))
    best_p = prob_map.get(best, global_p)

    return {
        "moves": [{"action": "reveal", "row": best[0], "col": best[1], "prob": round(best_p, 3)}],
        "is_guess": True,
    }


# ── Probability heatmap ───────────────────────────────────────────────────────

def build_prob_map(board: list[list[Cell]]) -> list[list[float | None]]:
    """Returns ROWS×COLS matrix of mine probability estimates (None = revealed/flagged)."""
    total_flagged = sum(cell.flagged for row in board for cell in row)
    all_unrev = [
        (r, c)
        for r in range(ROWS)
        for c in range(COLS)
        if not board[r][c].revealed and not board[r][c].flagged
    ]
    global_p = (MINES - total_flagged) / len(all_unrev) if all_unrev else 0.0

    result: list[list[float | None]] = [[None] * COLS for _ in range(ROWS)]
    for r, c in all_unrev:
        result[r][c] = global_p

    for r in range(ROWS):
        for c in range(COLS):
            cell = board[r][c]
            if not cell.revealed or cell.n == 0:
                continue
            ns = get_neighbors(r, c)
            unrev = [(nr, nc) for nr, nc in ns if not board[nr][nc].revealed and not board[nr][nc].flagged]
            n_flagged = sum(1 for nr, nc in ns if board[nr][nc].flagged)
            remaining = cell.n - n_flagged
            if unrev and remaining >= 0:
                p = remaining / len(unrev)
                for nr, nc in unrev:
                    if result[nr][nc] is not None:
                        result[nr][nc] = max(result[nr][nc], p)

    return result
