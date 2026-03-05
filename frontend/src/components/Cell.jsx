const NUM_COLORS = ['','#0000fe','#017700','#fe0000','#010180','#870000','#008484','#840000','#808080']

export default function Cell({ cell, hlType, prob, isChordHighlight, row, col, onReveal, onFlag, onChord, onChordPress }) {
  const { mine, revealed, flagged, n } = cell
  let bg = '#c0c0c0', cellClass = 'cell cell-raised', content = null

  if (revealed) {
    cellClass = 'cell cell-flat'
    if (mine) { bg = '#ff5555'; content = <span className="cell-icon">💣</span> }
    else if (n > 0) content = <span className="cell-num" style={{ color: NUM_COLORS[n] }}>{n}</span>
  } else {
    if (flagged)              content = <span className="cell-icon">🚩</span>
    else if (isChordHighlight) bg = '#99ffdd'
    else if (hlType === 'flag')   bg = '#ffe566'
    else if (hlType === 'reveal') bg = '#99ffdd'
  }

  // Clicking a revealed numbered cell = chord (reveal neighbours if flags match)
  const handleClick = () => {
    if (revealed && n > 0) onChord()
    else if (!revealed && !flagged) onReveal()
  }

  const handleMouseDown = () => {
    if (revealed && n > 0 && onChordPress) onChordPress(row, col)
  }

  return (
    <div className={cellClass} style={{ background: bg, position: 'relative' }}
      onClick={handleClick} onMouseDown={handleMouseDown} onContextMenu={onFlag}>
      {!revealed && !flagged && prob != null && (
        <div className="prob-overlay" style={{
          background: `rgba(${Math.round(255*prob)},${Math.round(200*(1-prob))},0,0.58)`,
        }} />
      )}
      {content}
    </div>
  )
}
