import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from game import Game, ROWS, COLS, MINES
from solver import csp_solve, build_prob_map
from db import init_db, get_saved_users, get_user, save_user

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger("minesweeper")

app = FastAPI(title="Minesweeper Multiplayer", version="2.0.0", docs_url="/docs")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Scoring constants ─────────────────────────────────────────────────────────
SCORE_WIN        = 500
SCORE_TIME_BONUS = 300   # max extra for finishing under 60 s
SCORE_CELL       = 2     # per revealed safe cell
SCORE_LOSS       = -100

PLAYER_COLORS = [
    "#00ff88", "#ff6b6b", "#4dabf7", "#ffd43b",
    "#cc5de8", "#ff922b", "#69db7c", "#f783ac",
]

# ── Player session ────────────────────────────────────────────────────────────

class PlayerSession:
    def __init__(self, pid: str, name: str, color: str):
        self.pid        = pid
        self.name       = name
        self.color      = color
        self.game       = Game()
        self.ws: Optional[WebSocket] = None
        self.score      = 0
        self.games      = 0
        self.wins       = 0
        self.best_time  = 0
        self.agent_cfg  = {
            "mode": "none", "speed": 500,
            "running": False, "auto_restart": False,
            "thinking": False,
        }
        self.agent_task: Optional[asyncio.Task] = None
        self.agent_log: list[dict] = []
        self.highlight: Optional[dict] = None
        self.show_prob  = False

    def add_log(self, msg: str, kind: str = "info"):
        self.agent_log.insert(0, {
            "msg": msg, "type": kind,
            "time": datetime.now().strftime("%H:%M:%S"),
        })
        del self.agent_log[80:]

    def to_public(self) -> dict:
        return {
            "pid":       self.pid,
            "name":      self.name,
            "color":     self.color,
            "score":     self.score,
            "games":     self.games,
            "wins":      self.wins,
            "best_time": self.best_time,
            "win_rate":  round(self.wins / self.games * 100) if self.games else 0,
            "status":    self.game.status,
        }

    def to_private(self) -> dict:
        return {
            "type":      "state",
            "game":      self.game.to_dict(),
            "agent":     dict(self.agent_cfg),
            "log":       self.agent_log[:60],
            "highlight": self.highlight,
            "prob_map":  build_prob_map(self.game.board) if self.show_prob else None,
            "me":        self.to_public(),
        }


# ── Global state ──────────────────────────────────────────────────────────────

sessions: dict[str, PlayerSession] = {}
chat_log: list[dict] = []


def next_color() -> str:
    used = {s.color for s in sessions.values()}
    for c in PLAYER_COLORS:
        if c not in used:
            return c
    return PLAYER_COLORS[len(sessions) % len(PLAYER_COLORS)]


# ── Broadcast helpers ─────────────────────────────────────────────────────────

def leaderboard() -> list[dict]:
    return sorted(
        [s.to_public() for s in sessions.values()],
        key=lambda x: x["score"], reverse=True,
    )

async def _send(ws: WebSocket, payload: dict):
    try:
        await ws.send_text(json.dumps(payload))
    except Exception:
        pass

async def broadcast_leaderboard():
    payload = {"type": "leaderboard", "players": leaderboard()}
    for s in sessions.values():
        if s.ws:
            await _send(s.ws, payload)

async def broadcast_chat():
    payload = {"type": "chat_update", "messages": chat_log[-60:]}
    for s in sessions.values():
        if s.ws:
            await _send(s.ws, payload)

async def push_state(session: PlayerSession):
    if session.ws:
        await _send(session.ws, session.to_private())
    await broadcast_leaderboard()


# ── Scoring ───────────────────────────────────────────────────────────────────

def compute_score(session: PlayerSession, result: str):
    if result == "won":
        elapsed    = session.game.elapsed
        time_bonus = max(0, SCORE_TIME_BONUS - elapsed * 3)
        revealed   = sum(1 for row in session.game.board for c in row if c.revealed and not c.mine)
        gain       = SCORE_WIN + int(time_bonus) + revealed * SCORE_CELL
        session.score += gain
        session.wins  += 1
        session.games += 1
        if session.best_time == 0 or elapsed < session.best_time:
            session.best_time = elapsed
        session.add_log(f"🏆 WIN! +{gain} pts (time bonus +{int(time_bonus)})", "success")
    elif result == "lost":
        session.score  = max(0, session.score + SCORE_LOSS)
        session.games += 1
        session.add_log(f"💥 BOOM! {SCORE_LOSS} pts", "error")


async def persist_user(session: PlayerSession):
    """Save user progress to local DB."""
    try:
        await save_user(
            session.name,
            session.score,
            session.games,
            session.wins,
            session.best_time,
        )
    except Exception as e:
        logger.warning(f"Failed to save user {session.name}: {e}")


# ── Per-player agent loop ─────────────────────────────────────────────────────

async def agent_loop(session: PlayerSession):
    while session.agent_cfg["running"]:
        g = session.game

        # Game ended (stats only updated on manual play, not CSP)
        if g.status in ("won", "lost"):
            session.agent_cfg["running"] = False
            await push_state(session)

            if session.agent_cfg["auto_restart"]:
                session.agent_cfg["running"] = True
                session.add_log("🔄 Auto-restarting…", "info")
                await push_state(session)
                await asyncio.sleep(1.5)
                session.game      = Game()
                session.highlight = None
                await push_state(session)
                await asyncio.sleep(0.3)
                continue
            break

        mode = session.agent_cfg["mode"]

        # ── CSP ──
        if mode == "rule":
            try:
                result = csp_solve(g.board)
            except Exception as exc:
                session.add_log(f"❌ Solver error: {exc}", "error")
                logger.exception("CSP solver error")
                session.agent_cfg["running"] = False
                await push_state(session)
                break

            moves  = result["moves"]

            if not moves:
                session.add_log("🤔 Solver stuck.", "warn")
                session.agent_cfg["running"] = False
                await push_state(session)
                break

            if result["is_guess"]:
                m   = moves[0]
                pct = f"{m.get('prob', 0)*100:.0f}%"
                session.add_log(f"🎲 GUESS ({m['row']},{m['col']}) — {pct}", "warn")
                session.highlight = {"row": m["row"], "col": m["col"], "action": "reveal"}
                await push_state(session)
                await asyncio.sleep(min(session.agent_cfg["speed"] / 1000 * 0.6, 0.5))
                res = g.reveal(m["row"], m["col"])
                if res in ("won", "lost"):
                    session.highlight = None
                    session.agent_cfg["running"] = False
                    await push_state(session)
                    if session.agent_cfg["auto_restart"]:
                        session.agent_cfg["running"] = True
                        session.add_log("🔄 Auto-restarting…", "info")
                        await push_state(session)
                        await asyncio.sleep(1.5)
                        session.game = Game(); session.highlight = None
                        await push_state(session)
                        await asyncio.sleep(0.3)
                        continue
                    break
            else:
                nf = sum(1 for m in moves if m["action"] == "flag")
                nr = sum(1 for m in moves if m["action"] == "reveal")
                session.add_log(f"✅ {nf} flag(s), {nr} reveal(s)", "info")
                done = False
                auto_restarted = False
                step_delay = max(session.agent_cfg["speed"] / 1000 * 0.12, 0.025)
                for m in moves:
                    if not session.agent_cfg["running"]:
                        done = True; break
                    session.highlight = {"row": m["row"], "col": m["col"], "action": m["action"]}
                    await push_state(session)                     # ← broadcast each move
                    await asyncio.sleep(step_delay)               # ← visible per-move delay
                    if m["action"] == "flag":
                        g.flag(m["row"], m["col"])
                    else:
                        res = g.reveal(m["row"], m["col"])
                        if res in ("won", "lost"):
                            session.highlight = None
                            session.agent_cfg["running"] = False
                            await push_state(session)
                            if session.agent_cfg["auto_restart"]:
                                session.agent_cfg["running"] = True
                                session.add_log("🔄 Auto-restarting…", "info")
                                await push_state(session)
                                await asyncio.sleep(1.5)
                                session.game = Game(); session.highlight = None
                                await push_state(session)
                                await asyncio.sleep(0.3)
                                done = True
                                auto_restarted = True
                            break
                if done and not auto_restarted:
                    break

        session.highlight = None
        await push_state(session)
        await asyncio.sleep(session.agent_cfg["speed"] / 1000)

    session.agent_cfg["running"] = False
    session.agent_cfg["thinking"] = False


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    pid = None
    try:
        raw = await ws.receive_text()
        msg = json.loads(raw)
        if msg.get("type") != "join":
            await ws.close(code=1008); return

        name    = (msg.get("name") or "Player").strip()[:20] or "Player"
        pid     = str(uuid4())[:8]
        color   = next_color()
        session = PlayerSession(pid, name, color)
        session.ws    = ws
        sessions[pid] = session
        # Load saved progress if this user exists in DB
        saved = await get_user(name)
        if saved:
            session.score = saved["score"]
            session.games = saved["games"]
            session.wins  = saved["wins"]
            session.best_time = saved["best_time"]
        await persist_user(session)  # ensure user appears in saved list / scoreboard
        logger.info(f"+ {name} ({pid}) — {len(sessions)} online")

        await push_state(session)
        await _send(ws, {"type": "chat_update", "messages": chat_log[-60:]})

        chat_log.append({"pid": "system", "name": "System", "color": "#666680",
                         "text": f"{name} joined! 👋", "time": datetime.now().strftime("%H:%M")})
        await broadcast_chat()
        await broadcast_leaderboard()

        while True:
            raw = await ws.receive_text()
            await handle_message(sessions[pid], json.loads(raw))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WS error ({pid}): {e}")
    finally:
        if pid and pid in sessions:
            s = sessions[pid]
            s.agent_cfg["running"] = False
            if s.agent_task and not s.agent_task.done():
                s.agent_task.cancel()
            await persist_user(s)
            del sessions[pid]
            chat_log.append({"pid": "system", "name": "System", "color": "#666680",
                             "text": f"{s.name} left.", "time": datetime.now().strftime("%H:%M")})
            await broadcast_chat()
            await broadcast_leaderboard()
            logger.info(f"- {s.name} ({pid}) — {len(sessions)} online")


async def handle_message(session: PlayerSession, msg: dict):
    t = msg.get("type")
    g = session.game

    if t == "reveal":
        if not session.agent_cfg["running"]:
            res = g.reveal(msg["row"], msg["col"])
            if res in ("won", "lost"):
                compute_score(session, res)
                await persist_user(session)
            await push_state(session)

    elif t == "chord":
        if not session.agent_cfg["running"]:
            res = g.chord(msg["row"], msg["col"])
            if res in ("won", "lost"):
                compute_score(session, res)
                await persist_user(session)
            await push_state(session)

    elif t == "flag":
        if not session.agent_cfg["running"]:
            g.flag(msg["row"], msg["col"])
            await push_state(session)

    elif t == "new_game":
        session.agent_cfg["running"] = False
        session.agent_cfg["thinking"] = False
        if session.agent_task and not session.agent_task.done():
            session.agent_task.cancel()
        session.game = Game(); session.highlight = None
        await push_state(session)

    elif t == "set_agent":
        session.agent_cfg["mode"]         = msg.get("mode", "none")
        session.agent_cfg["speed"]        = msg.get("speed", 500)
        session.agent_cfg["auto_restart"] = msg.get("auto_restart", False)
        await push_state(session)

    elif t == "start_agent":
        if not session.agent_cfg["running"] and session.agent_cfg["mode"] != "none":
            session.agent_cfg["running"] = True
            session.add_log("🚀 CSP agent started.", "success")
            if session.agent_task and not session.agent_task.done():
                session.agent_task.cancel()
            session.agent_task = asyncio.create_task(agent_loop(session))
            await push_state(session)

    elif t == "stop_agent":
        session.agent_cfg["running"] = False
        session.agent_cfg["thinking"] = False
        if session.agent_task and not session.agent_task.done():
            session.agent_task.cancel()
        session.add_log("⏹ Agent stopped.", "info")
        await push_state(session)

    elif t == "toggle_prob_map":
        session.show_prob = msg.get("enabled", False)
        await push_state(session)

    elif t == "chat":
        text = (msg.get("text") or "").strip()[:200]
        if text:
            chat_log.append({"pid": session.pid, "name": session.name, "color": session.color,
                             "text": text, "time": datetime.now().strftime("%H:%M")})
            del chat_log[200:]
            await broadcast_chat()


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/api/saved-users")
async def api_saved_users():
    """List all saved users (for join screen and scoreboard)."""
    users = await get_saved_users()
    return {"users": users}


@app.get("/health")
def health():
    return {"status": "ok", "players": len(sessions)}
