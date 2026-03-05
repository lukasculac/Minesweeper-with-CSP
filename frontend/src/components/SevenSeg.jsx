export default function SevenSeg({ value }) {
  const v = Math.max(0, Math.min(999, Math.floor(value ?? 0)))
  return <div className="seven-seg">{String(v).padStart(3, '0')}</div>
}
