# 💣 Minesweeper · A.I. — Multiplayer

Real-time multiplayer Minesweeper with AI agents, live scoring, and chat.
Each player gets their own board. Scores accumulate across games.

```
FastAPI backend  ←→  WebSocket  ←→  React/Vite frontend
```

---

## Hosting for friends on the same WiFi

Everyone just opens a browser — **they install nothing**.

### Step 1 — Find your laptop's local IP

**Windows:**
```
ipconfig
```
Look for "IPv4 Address" under your WiFi adapter, e.g. `192.168.1.42`

**Mac/Linux:**
```
ifconfig | grep "inet "
# or
ip addr show
```
Look for something like `192.168.1.42` (not `127.0.0.1`)

### Step 2 — Start the game (pick one method)

**Option A — Docker or Podman (recommended, one command):**
```bash
docker-compose up --build
# or
podman compose up --build
```
Then open **http://localhost:8080** in your browser (note the port `:8080`).

**Option B — Manual (two terminals):**
```bash
# Terminal 1 — backend
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — frontend
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

> `--host 0.0.0.0` is critical — it makes the server accessible to other devices on the network.
> Without it, the server only listens on localhost and friends can't connect.

### Step 3 — Share the URL with your friends

1. **Find your PC’s IP** (same WiFi as your friends):
   - **Windows:** Open CMD or PowerShell → run `ipconfig` → use the **IPv4 Address** under your WiFi adapter (e.g. `192.168.1.42`).
   - **Mac:** System Settings → Network → Wi‑Fi → Details, or run `ipconfig getifaddr en0`.
2. **Send this link** (replace with your IP):
   ```
   http://192.168.1.42:8080   ← Docker / Podman
   http://192.168.1.42:5173   ← Manual dev server
   ```
3. Friends open that link in their browser, enter a name, and play.

**If friends can’t connect:**  
- **Windows:** Allow port 8080 through the firewall (Windows Security → Firewall → Advanced → Inbound rules → New rule → Port → TCP 8080 → Allow).  
- **Podman on Windows:** The Podman VM may only expose ports to your PC. If friends still can’t reach you, try running without Docker (Option B above) so the app listens directly on your machine.

### Podman (Windows / WSL2)

If you use **Podman** instead of Docker and see errors like `no container with name or ID "minesweeper-frontend" found`:

1. **WSL2 / Podman machine:** Pod creation can fail due to cgroups. Set the cgroup manager to `cgroupfs` in Podman’s config:
   - **Linux/WSL:** Edit `~/.config/containers/containers.conf` (or `/etc/containers/containers.conf`) and set:
     ```ini
     [engine]
     cgroup_manager = "cgroupfs"
     ```
   - **Windows (Podman Desktop / native):** If you use a Podman “machine” (VM), ensure the VM uses cgroupfs, or use the built-in Compose plugin: `podman compose up --build` (no hyphen) if available.

2. **Port:** The app is set to use **port 8080** on the host (not 80) so you don’t need admin rights and to avoid conflicts. Open `http://<your-ip>:8080`.

3. **Compose command:** Prefer `podman compose up --build` (Podman’s built-in plugin) over `podman-compose` when possible.

### Windows: "WinError 10013" when running the backend manually

This usually means **port 8000 is in use or reserved** by Windows.

1. **If you use Docker/Podman:** Stop the stack so it releases port 8000:
   ```bash
   podman compose down
   # or: docker-compose down
   ```
2. **If it still happens:** Windows (or Hyper-V/WSL) may have reserved the port. Use port **8001** instead:
   - **Terminal 1 (backend):**
     ```bash
     cd backend
     uvicorn main:app --host 0.0.0.0 --port 8001 --reload
     ```
   - **Terminal 2 (frontend):** Tell Vite to use 8001:
     ```bash
     cd frontend
     set VITE_BACKEND_PORT=8001
     npm run dev -- --host 0.0.0.0
     ```
     (On PowerShell: `$env:VITE_BACKEND_PORT=8001` then `npm run dev -- --host 0.0.0.0`.)

---

## How scoring works

| Event | Points |
|-------|--------|
| Win   | +500 base |
| Time bonus | up to +300 (decreases by 3 pts/sec) |
| Each safe cell revealed | +2 |
| Loss | −100 |
| Minimum score | 0 (never goes negative) |

The live leaderboard in the top bar updates in real-time for all players.

---

## Features

- **Each player has their own independent board** — you play your own game, not each other's
- **Live leaderboard** — top bar shows all connected players ranked by score with medals 🥇🥈🥉
- **Chat** — right sidebar, hit Enter or SEND. System messages announce join/leave events.
- **AI agents** — each player can run their own agent independently:
  - 🔧 CSP — deterministic constraint solver + probabilistic fallback
- **Probability heatmap** — green→red mine probability overlay
- **Auto-restart** — agent keeps playing games and accumulating score automatically

---

## Project layout

```
minesweeper-ai/
├── backend/
│   ├── main.py      ← FastAPI, WebSocket hub, per-player agent loops, chat, scoring
│   ├── game.py      ← Board logic (mine placement, flood-fill reveal, win/loss)
│   ├── solver.py    ← CSP constraint solver + probability heatmap
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.jsx              ← Join screen + main layout + WebSocket
│       └── components/
│           ├── Board.jsx        ← Win95-style game board
│           ├── Cell.jsx         ← Individual cell with heatmap overlay
│           ├── Panel.jsx        ← AI controls + personal stats + agent log
│           ├── Chat.jsx         ← Live chat sidebar
│           ├── Leaderboard.jsx  ← Top bar player rankings
│           └── SevenSeg.jsx     ← Red LED counter display
└── docker-compose.yml
```

---

## WebSocket message reference

**Client → server:**
```json
{ "type": "join",            "name": "Alice" }
{ "type": "reveal",          "row": 3, "col": 7 }
{ "type": "flag",            "row": 3, "col": 7 }
{ "type": "new_game" }
{ "type": "chat",            "text": "good luck!" }
{ "type": "set_agent",       "mode": "rule", "speed": 500, "auto_restart": false }
{ "type": "start_agent" }
{ "type": "stop_agent" }
{ "type": "toggle_prob_map", "enabled": true }
```

**Server → client (three message types):**
```json
// 1. Your private game state (sent after every action)
{ "type": "state", "game": {...}, "agent": {...}, "log": [...], "highlight": {...}, "prob_map": [[...]], "me": {...} }

// 2. Leaderboard (broadcast to all players after any score change)
{ "type": "leaderboard", "players": [{ "name": "Alice", "score": 842, "status": "playing", ... }] }

// 3. Chat (broadcast to all players)
{ "type": "chat_update", "messages": [{ "name": "Alice", "text": "gg", "time": "14:22" }] }
```
