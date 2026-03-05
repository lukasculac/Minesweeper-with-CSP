import { useState, useCallback } from 'react'
import Cell from './Cell'
import SevenSeg from './SevenSeg'

function face(status, agentRunning) {
  if (status === 'won')  return '😎'
  if (status === 'lost') return '😵'
  if (agentRunning)      return '🤖'
  return '🙂'
}

function getUnopenedNeighbours(board, r, c) {
  const rows = board.length
  const cols = board[0]?.length ?? 0
  const out = []
  for (let dr = -1; dr <= 1; dr++) {
    for (let dc = -1; dc <= 1; dc++) {
      if (dr === 0 && dc === 0) continue
      const nr = r + dr
      const nc = c + dc
      if (nr >= 0 && nr < rows && nc >= 0 && nc < cols) {
        const cell = board[nr][nc]
        if (!cell.revealed && !cell.flagged) out.push({ row: nr, col: nc })
      }
    }
  }
  return out
}

export default function Board({ board, status, highlight, probMap, minesLeft, elapsed, agentRunning, onReveal, onFlag, onChord, onReset }) {
  const [chordHighlight, setChordHighlight] = useState([])

  const onChordPress = useCallback((r, c) => {
    const cell = board[r]?.[c]
    if (cell?.revealed && cell?.n > 0) {
      setChordHighlight(getUnopenedNeighbours(board, r, c))
    }
  }, [board])

  const onChordRelease = useCallback(() => {
    setChordHighlight([])
  }, [])

  return (
    <div className="board-wrapper">
      <div className="ms-board">
        <div className="ms-header">
          <SevenSeg value={minesLeft} />
          <button className="smiley-btn" onClick={onReset}>{face(status, agentRunning)}</button>
          <SevenSeg value={elapsed} />
        </div>
        <div className="ms-grid"
          onMouseLeave={onChordRelease}
          onMouseUp={onChordRelease}>
          {board.map((row, r) => row.map((cell, c) => {
            const isHl = highlight && highlight.row === r && highlight.col === c
            const isChordHl = chordHighlight.some(p => p.row === r && p.col === c)
            return (
              <Cell key={`${r}-${c}`} row={r} col={c} cell={cell}
                hlType={isHl ? highlight.action : null}
                isChordHighlight={isChordHl}
                prob={probMap?.[r]?.[c] ?? null}
                onReveal={() => onReveal(r, c)}
                onFlag={e => { e.preventDefault(); onFlag(r, c) }}
                onChord={() => onChord(r, c)}
                onChordPress={onChordPress}
              />
            )
          }))}
        </div>
      </div>
      <div className={`status-bar ${status}`}>
        {status === 'won'     && '✦  BOARD CLEARED — YOU WIN  ✦'}
        {status === 'lost'    && '✦  MINE DETONATED — GAME OVER  ✦'}
        {status === 'idle'    && '·  CLICK ANY CELL OR START AN AGENT  ·'}
        {status === 'playing' && '·  GAME IN PROGRESS  ·'}
      </div>
    </div>
  )
}
