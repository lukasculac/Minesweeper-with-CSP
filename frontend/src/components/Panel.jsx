import { useState } from 'react'

const LOG_COLOR = { error: '#ff5566', success: '#00ff88', warn: '#ffaa00', info: '#8899cc' }
const MODES = [['none', '👁 WATCH'], ['rule', '🔧 CSP']]

export default function Panel({ me, agent, log, onSetAgent, onStart, onStop, onNewGame, onToggleProbMap }) {
  const [probMap, setProbMap] = useState(false)

  const push = patch => onSetAgent({ mode: agent.mode, speed: agent.speed, auto_restart: agent.auto_restart, ...patch })
  const winRate = me.games > 0 ? ((me.wins / me.games) * 100).toFixed(0) : '—'
  const speedLabel = agent.speed < 1000 ? `${agent.speed}ms` : `${(agent.speed / 1000).toFixed(1)}s`

  const handleProb = v => { setProbMap(v); onToggleProbMap(v) }

  return (
    <div className="panel">
      <div className="panel-card">
        <div className="panel-title">◈ MY STATS</div>
        <div className="stats-grid">
          {[['SCORE', me.score], ['GAMES', me.games], ['WINS', me.wins],
            ['WIN %', `${winRate}%`], ['BEST', me.best_time ? `${me.best_time}s` : '—']].map(([l, v]) => (
            <div className="stat-item" key={l}>
              <div className="stat-label">{l}</div>
              <div className="stat-val">{v}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="panel-card">
        <div className="panel-title">◈ AI AGENT</div>
        <div className="mode-buttons">
          {MODES.map(([m, lbl]) => (
            <button key={m} className={`mode-btn ${agent.mode === m ? 'active' : ''}`}
              onClick={() => { if (!agent.running) push({ mode: m }) }}
              disabled={agent.running}>{lbl}</button>
          ))}
        </div>

        <div className="speed-section">
          <div className="speed-header">
            <span className="field-label" style={{ marginBottom: 0 }}>SPEED</span>
            <span className="speed-val">{speedLabel} / step</span>
          </div>
          <input type="range" className="speed-slider" min="50" max="2000" step="50"
            value={agent.speed} onChange={e => push({ speed: +e.target.value })} />
          <div className="speed-labels"><span>FAST</span><span>SLOW</span></div>
        </div>

        <label className="toggle-label">
          <input type="checkbox" checked={agent.auto_restart}
            onChange={e => push({ auto_restart: e.target.checked })} />
          AUTO-RESTART
        </label>

        <label className="toggle-label">
          <input type="checkbox" checked={probMap} onChange={e => handleProb(e.target.checked)} />
          MINE PROBABILITY HEATMAP
        </label>
        {probMap && (
          <div className="prob-legend">
            <div className="prob-gradient" />
            <span>0% → 100% mine</span>
          </div>
        )}

        <div className="agent-controls">
          <button className={`ctrl-btn ${agent.running ? 'stop' : 'start'}`}
            onClick={agent.running ? onStop : onStart} disabled={agent.mode === 'none'}>
            {agent.running ? '⏹ STOP' : '▶ START'}
          </button>
          <button className="ctrl-btn new" onClick={onNewGame}>↺ NEW</button>
        </div>
      </div>

      <div className="panel-card log-card">
        <div className="log-header">
          <div className="panel-title" style={{ margin: 0, border: 'none', padding: 0 }}>◈ AGENT LOG</div>
          {agent.thinking && <span className="thinking-dot">⊙ THINKING</span>}
        </div>
        <div className="log-scroll">
          {log.length === 0
            ? <div className="log-empty">Awaiting activation…</div>
            : log.map((e, i) => (
              <div key={i} className="log-entry" style={{ color: LOG_COLOR[e.type] ?? '#8899cc' }}>
                <span className="log-time">{e.time}</span>{e.msg}
              </div>
            ))}
        </div>
      </div>
    </div>
  )
}
