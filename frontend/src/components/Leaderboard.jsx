const STATUS_LABEL = { idle: '·', playing: '▶', won: '✦', lost: '✕' }
const STATUS_COLOR = { idle: '#2a2a38', playing: '#00ff88', won: '#ffd43b', lost: '#ff4455' }

const medals = ['🥇', '🥈', '🥉']

export default function Leaderboard({ players }) {
  if (!players.length) return null
  return (
    <div className="lb-bar">
      {players.map((p, i) => (
        <div key={p.pid} className="lb-entry">
          <span className="lb-rank">{medals[i] ?? `#${i + 1}`}</span>
          <span className="badge-dot" style={{ background: p.color }} />
          <span className="lb-name">{p.name}</span>
          <span className="lb-score" style={{ color: p.color }}>{p.score}</span>
          <span className="lb-status" style={{ color: STATUS_COLOR[p.status] }}>
            {STATUS_LABEL[p.status] ?? '·'}
          </span>
        </div>
      ))}
    </div>
  )
}
