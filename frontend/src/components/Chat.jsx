import { useEffect, useRef, useState } from 'react'

export default function Chat({ messages, onSend, onlineCount }) {
  const [input, setInput] = useState('')
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = () => {
    const txt = input.trim()
    if (!txt) return
    onSend(txt)
    setInput('')
  }

  return (
    <div className="chat-sidebar">
      <div className="chat-title">
        <span>◈ CHAT</span>
        <span className="chat-online">{onlineCount} online</span>
      </div>

      <div className="chat-messages">
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg ${m.pid === 'system' ? 'chat-msg-system' : ''}`}>
            <div className="chat-meta">
              <span className="chat-name" style={{ color: m.color }}>{m.name}</span>
              <span className="chat-time">{m.time}</span>
            </div>
            <div className="chat-text">{m.text}</div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-row">
        <input
          className="chat-input"
          placeholder="Say something…"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send()}
          maxLength={200}
        />
        <button className="chat-send" onClick={send}>SEND</button>
      </div>
    </div>
  )
}
