import { useState, useEffect, useCallback, useRef } from 'react'
import Board from './components/Board'
import Panel from './components/Panel'
import Chat from './components/Chat'
import Leaderboard from './components/Leaderboard'

const EMPTY_BOARD = Array.from({ length: 16 }, () =>
  Array.from({ length: 30 }, () => ({ revealed: false, flagged: false, mine: false, n: 0 }))
)

const DEFAULT_STATE = {
  game:      { board: EMPTY_BOARD, status: 'idle', elapsed: 0, mines_left: 99 },
  agent:     { mode: 'none', speed: 500, running: false, auto_restart: false, thinking: false },
  log:       [],
  highlight: null,
  prob_map:  null,
  me:        { pid: '', name: '', color: '#00ff88', score: 0, games: 0, wins: 0, best_time: 0, win_rate: 0, status: 'idle' },
}

function wsUrl() {
  if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/ws`
}

// ── Join screen ───────────────────────────────────────────────────────────────
function JoinScreen({ onJoin }) {
  const [name, setName] = useState('')
  const [savedUsers, setSavedUsers] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/saved-users')
      .then(r => r.json())
      .then(data => { setSavedUsers(data.users || []); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const submit = () => { const n = name.trim(); if (n) onJoin(n) }
  const loadUser = (u) => { setName(u.name); }

  return (
    <div className="join-screen">
      <div className="join-layout">
        <div className="join-card">
          <div className="join-title">💣 MINESWEEPER</div>
          <div className="join-sub">
            MULTIPLAYER · AI AGENT · LIVE SCORING<br />
            30 × 16 · 99 MINES · EXPERT
          </div>
          <input
            className="name-input"
            placeholder="ENTER YOUR NAME"
            value={name}
            maxLength={20}
            onChange={e => setName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && submit()}
            autoFocus
          />
          <button className="join-btn" onClick={submit} disabled={!name.trim()}>
            ▶ JOIN GAME
          </button>

          {savedUsers.length > 0 && (
            <div className="saved-users-block">
              <div className="saved-users-title">Load saved account</div>
              <div className="saved-users-list">
                {savedUsers.slice(0, 8).map((u, i) => (
                  <button
                    key={u.name}
                    type="button"
                    className={`saved-user-btn ${name === u.name ? 'active' : ''}`}
                    onClick={() => loadUser(u)}
                  >
                    {u.name}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="scoreboard-window">
          <div className="scoreboard-title">◈ SCOREBOARD</div>
          {loading ? (
            <div className="scoreboard-empty">Loading…</div>
          ) : savedUsers.length === 0 ? (
            <div className="scoreboard-empty">No saved players yet</div>
          ) : (
            <div className="scoreboard-list">
              {savedUsers.map((u, i) => (
                <div key={u.name} className="scoreboard-row">
                  <span className="sb-rank">#{i + 1}</span>
                  <span className="sb-name">{u.name}</span>
                  <span className="sb-score">{u.score}</span>
                  <span className="sb-meta">{u.wins}W / {u.games}G · best {u.best_time}s</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Main app ──────────────────────────────────────────────────────────────────
export default function App() {
  const [phase,       setPhase]       = useState('join')   // 'join' | 'game'
  const [playerName,  setPlayerName]  = useState('')
  const [serverState, setServerState] = useState(DEFAULT_STATE)
  const [players,     setPlayers]     = useState([])
  const [chatMsgs,    setChatMsgs]    = useState([])
  const [connected,   setConnected]   = useState(false)

  const wsRef    = useRef(null)
  const retryRef = useRef(null)
  const nameRef  = useRef('')

  const connect = useCallback((name) => {
    nameRef.current = name
    if (wsRef.current) wsRef.current.close()

    const ws = new WebSocket(wsUrl())
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      clearTimeout(retryRef.current)
      ws.send(JSON.stringify({ type: 'join', name }))
    }

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data)
      if (data.type === 'state')        setServerState(data)
      if (data.type === 'leaderboard')  setPlayers(data.players)
      if (data.type === 'chat_update')  setChatMsgs(data.messages)
    }

    ws.onclose = () => {
      setConnected(false)
      retryRef.current = setTimeout(() => connect(nameRef.current), 2000)
    }

    ws.onerror = () => ws.close()
  }, [])

  useEffect(() => () => {
    clearTimeout(retryRef.current)
    wsRef.current?.close()
  }, [])

  const send = useCallback((msg) => {
    if (wsRef.current?.readyState === WebSocket.OPEN)
      wsRef.current.send(JSON.stringify(msg))
  }, [])

  const handleJoin = (name) => {
    setPlayerName(name)
    setPhase('game')
    connect(name)
  }

  const actions = {
    reveal:        (r, c)    => send({ type: 'reveal', row: r, col: c }),
    chord:         (r, c)    => send({ type: 'chord',  row: r, col: c }),
    flag:          (r, c)    => send({ type: 'flag',   row: r, col: c }),
    newGame:       ()        => send({ type: 'new_game' }),
    setAgent:      (cfg)     => send({ type: 'set_agent', ...cfg }),
    startAgent:    ()        => send({ type: 'start_agent' }),
    stopAgent:     ()        => send({ type: 'stop_agent' }),
    toggleProbMap: (enabled) => send({ type: 'toggle_prob_map', enabled }),
    chat:          (text)    => send({ type: 'chat', text }),
  }

  if (phase === 'join') return <JoinScreen onJoin={handleJoin} />

  const { game, agent, log, highlight, prob_map, me } = serverState

  return (
    <div className="app">
      <div className="topbar">
        <span className="topbar-title">◈ MINESWEEPER · A.I.</span>
        <Leaderboard players={players} />
        <div className="topbar-right">
          {!connected && <span className="reconnect-msg">⚠ RECONNECTING…</span>}
          <div className="player-badge">
            <div className="badge-dot" style={{ background: me.color }} />
            <span className="player-name" style={{ color: me.color }}>{me.name || playerName}</span>
            <span className="player-sep">·</span>
            <span className="player-score">{me.score} pts</span>
          </div>
        </div>
      </div>

      <div className="main-area">
        <Chat
          messages={chatMsgs}
          onSend={actions.chat}
          onlineCount={players.length}
        />
        <div className="game-wrap">
          <Board
            board={game.board}
            status={game.status}
            highlight={highlight}
            probMap={prob_map}
            minesLeft={game.mines_left}
            elapsed={game.elapsed}
            agentRunning={agent.running}
            onReveal={actions.reveal}
            onChord={actions.chord}
            onFlag={actions.flag}
            onReset={actions.newGame}
          />
        </div>
        <Panel
          me={me}
          agent={agent}
          log={log}
          onSetAgent={actions.setAgent}
          onStart={actions.startAgent}
          onStop={actions.stopAgent}
          onNewGame={actions.newGame}
          onToggleProbMap={actions.toggleProbMap}
        />
      </div>
    </div>
  )
}
