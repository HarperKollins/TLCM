import { useState, useEffect, useCallback, useRef } from 'react'
import { BrainCircuit, Database, History, Zap, Activity, Plus, Search, Cpu, Bell } from 'lucide-react'
import NetworkGraph from './components/NetworkGraph'

const API_URL = `${window.location.origin}/api/v1`

// ─── Reusable Modal Shell ─────────────────────────────────────────────────────
const Modal = ({ title, onClose, children }) => (
  <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
    <div className="glass-panel animate-fade-in" style={{ width: '480px', maxWidth: '90vw', padding: '32px', border: '1px solid var(--accent-cyan)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h2 style={{ color: 'var(--accent-cyan)', fontSize: '1.2rem', fontWeight: 700 }}>{title}</h2>
        <button onClick={onClose} style={{ border: 'none', background: 'transparent', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '1.4rem', padding: '0 4px' }}>✕</button>
      </div>
      {children}
    </div>
  </div>
)

// ─── Memory Timeline View ─────────────────────────────────────────────────────
const MemoryTree = ({ history }) => (
  <div className="animate-fade-in" style={{ padding: '16px', background: 'var(--bg-obsidian)', border: '1px solid var(--border-glass)', borderRadius: '8px', marginTop: '12px' }}>
    <h4 style={{ color: 'var(--accent-purple)', marginBottom: '12px', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Belief Arc (Version Chain)</h4>
    {history.map((mem, idx) => (
      <div key={mem.id} style={{ display: 'flex', alignItems: 'flex-start' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginRight: '14px' }}>
          <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: 'var(--accent-cyan)', boxShadow: '0 0 6px var(--accent-cyan)', flexShrink: 0 }} />
          {idx !== history.length - 1 && <div style={{ width: '2px', minHeight: '36px', background: 'var(--border-glass)' }} />}
        </div>
        <div style={{ paddingBottom: idx !== history.length - 1 ? '12px' : '0' }}>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '3px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            v{mem.version} · {new Date(mem.created_at).toLocaleString()}
          </div>
          <p style={{ color: 'var(--text-main)', fontSize: '0.9rem' }}>{mem.content}</p>
          {mem.update_reason && (
            <div style={{ fontSize: '0.8rem', fontStyle: 'italic', color: 'var(--accent-purple)', marginTop: '6px', paddingLeft: '10px', borderLeft: '2px solid var(--accent-purple)' }}>
              {mem.update_reason}
            </div>
          )}
        </div>
      </div>
    ))}
  </div>
)

// ─── Epoch Memory Panel ───────────────────────────────────────────────────────
const EpochMemories = ({ workspace, epoch, lastEventTime }) => {
  const [memories, setMemories] = useState([])
  const [historyMap, setHistoryMap] = useState({})
  const [expandedId, setExpandedId] = useState(null)

  const fetchMemories = useCallback(() => {
    fetch(`${API_URL}/memories/workspace/${workspace.name}/epoch/${epoch.name}`)
      .then(r => r.json()).then(data => {
        setMemories(data)
        data.forEach(mem => {
          if (!historyMap[mem.id]) {
            fetch(`${API_URL}/memories/${mem.id}/history`).then(r => r.json())
              .then(h => setHistoryMap(prev => ({ ...prev, [mem.id]: h })))
              .catch(() => {})
          }
        })
      }).catch(() => {})
  }, [workspace, epoch])

  useEffect(() => { fetchMemories() }, [fetchMemories, lastEventTime])

  if (memories.length === 0) return (
    <div style={{ padding: '16px', color: 'var(--text-muted)', fontSize: '0.9rem' }}>No memories in this epoch yet.</div>
  )

  return (
    <div style={{ marginTop: '16px' }}>
      <NetworkGraph memories={memories} historyMap={historyMap} />
      <div style={{ marginTop: '20px' }}>
        {memories.map(m => (
          <div key={m.id} className="glass-panel hover-glow" style={{ marginBottom: '12px', padding: '18px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
              <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontFamily: 'monospace' }}>#{m.id.substring(0, 10)}</span>
              <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                <span style={{ color: m.confidence > 0.7 ? 'var(--accent-cyan)' : 'var(--text-muted)', fontSize: '0.75rem' }}>
                  C: {(m.confidence * 100).toFixed(0)}%
                </span>
                <span style={{ color: 'var(--accent-purple)', fontSize: '0.75rem', fontWeight: 700 }}>v{m.version}</span>
              </div>
            </div>
            <p style={{ fontSize: '0.95rem', lineHeight: '1.5', textDecoration: m.reconsolidation_flag === 'orphaned_via_surgery' ? 'line-through' : 'none', color: m.reconsolidation_flag === 'orphaned_via_surgery' ? '#888' : 'var(--text-main)' }}>
              {m.content}
            </p>
            {m.reconsolidation_flag === 'orphaned_via_surgery' && (
              <span style={{ fontSize: '0.72rem', color: '#da6b6b', background: 'rgba(218,107,107,0.1)', padding: '2px 8px', borderRadius: '4px', marginTop: '6px', display: 'inline-block' }}>
                ✂ Orphaned via Graph Surgery
              </span>
            )}
            {historyMap[m.id] && historyMap[m.id].length > 1 && (
              <button onClick={() => setExpandedId(expandedId === m.id ? null : m.id)}
                style={{ marginTop: '10px', fontSize: '0.8rem', padding: '4px 12px', border: '1px solid var(--border-glass)', color: 'var(--accent-purple)' }}>
                {expandedId === m.id ? 'Hide' : `View`} Belief Arc ({historyMap[m.id].length} versions)
              </button>
            )}
            {expandedId === m.id && historyMap[m.id] && <MemoryTree history={historyMap[m.id]} />}
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── SSE Activity Feed ────────────────────────────────────────────────────────
const ActivityFeed = ({ events }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
    {events.length === 0 && <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Listening for memory events…</p>}
    {events.map((ev, i) => (
      <div key={i} className="animate-fade-in" style={{ padding: '10px 14px', background: 'rgba(100,255,218,0.04)', border: '1px solid var(--border-glass)', borderLeft: '3px solid var(--accent-cyan)', borderRadius: '6px' }}>
        <div style={{ fontSize: '0.72rem', color: 'var(--accent-cyan)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>
          {ev.type || 'event'} · {new Date(ev.timestamp || Date.now()).toLocaleTimeString()}
        </div>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-main)' }}>
          {ev.content ? `"${ev.content.substring(0, 90)}${ev.content.length > 90 ? '…' : ''}"` : JSON.stringify(ev).substring(0, 120)}
        </p>
      </div>
    ))}
  </div>
)

// ─── Main App ─────────────────────────────────────────────────────────────────
function App() {
  const [workspaces, setWorkspaces] = useState([])
  const [activeWorkspace, setActiveWorkspace] = useState(null)
  const [epochs, setEpochs] = useState([])
  const [activeTab, setActiveTab] = useState('hub')
  const [feedEvents, setFeedEvents] = useState([])

  // Modals
  const [showCreateWs, setShowCreateWs] = useState(false)
  const [showCreateEpoch, setShowCreateEpoch] = useState(false)
  const [showStoreMemory, setShowStoreMemory] = useState(false)
  const [showRecall, setShowRecall] = useState(false)

  // Form state
  const [wsForm, setWsForm] = useState({ name: '', description: '' })
  const [epochForm, setEpochForm] = useState({ name: '', description: '' })
  const [memoryForm, setMemoryForm] = useState({ content: '', epoch: '', source: 'user_stated' })
  const [recallForm, setRecallForm] = useState({ query: '', limit: 5 })
  const [recallResults, setRecallResults] = useState(null)

  // Jump state
  const [jumpFrom, setJumpFrom] = useState('')
  const [jumpTo, setJumpTo] = useState('')
  const [jumpDelta, setJumpDelta] = useState(null)
  const [isJumping, setIsJumping] = useState(false)

  // SSE live reload
  const [lastEventTime, setLastEventTime] = useState(Date.now())

  // Loading / error
  const [formLoading, setFormLoading] = useState(false)
  const [formError, setFormError] = useState('')

  // SSE Connection
  useEffect(() => {
    const source = new EventSource(`${API_URL}/events`)
    source.onmessage = (e) => {
      try {
        const payload = JSON.parse(e.data)
        if (payload.type !== 'ping') {
          setFeedEvents(prev => [{ ...payload, timestamp: Date.now() }, ...prev].slice(0, 15))
          setLastEventTime(Date.now())
        }
      } catch {}
    }
    return () => source.close()
  }, [])

  // Fetch workspaces
  const fetchWorkspaces = useCallback(() => {
    fetch(`${API_URL}/workspaces/`).then(r => r.json()).then(setWorkspaces).catch(() => {})
  }, [])

  useEffect(() => { fetchWorkspaces() }, [fetchWorkspaces, lastEventTime])

  // Fetch epochs when workspace changes
  useEffect(() => {
    if (activeWorkspace) {
      fetch(`${API_URL}/epochs/${activeWorkspace.name}`).then(r => r.json()).then(setEpochs).catch(() => {})
    }
  }, [activeWorkspace, lastEventTime])

  // ── Actions ──────────────────────────────────────────────────────────────────
  const createWorkspace = async () => {
    if (!wsForm.name.trim()) { setFormError('Workspace name is required.'); return }
    setFormLoading(true); setFormError('')
    try {
      const res = await fetch(`${API_URL}/workspaces/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(wsForm) })
      if (!res.ok) throw new Error((await res.json()).detail)
      fetchWorkspaces(); setShowCreateWs(false); setWsForm({ name: '', description: '' })
    } catch (e) { setFormError(e.message) }
    setFormLoading(false)
  }

  const createEpoch = async () => {
    if (!epochForm.name.trim()) { setFormError('Epoch name is required.'); return }
    setFormLoading(true); setFormError('')
    try {
      const res = await fetch(`${API_URL}/epochs/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ workspace: activeWorkspace.name, ...epochForm }) })
      if (!res.ok) throw new Error((await res.json()).detail)
      setShowCreateEpoch(false); setEpochForm({ name: '', description: '' }); setLastEventTime(Date.now())
    } catch (e) { setFormError(e.message) }
    setFormLoading(false)
  }

  const storeMemory = async () => {
    if (!memoryForm.content.trim()) { setFormError('Memory content is required.'); return }
    setFormLoading(true); setFormError('')
    try {
      const res = await fetch(`${API_URL}/memories/remember/sync`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workspace: activeWorkspace.name, content: memoryForm.content, epoch: memoryForm.epoch || undefined, source: memoryForm.source })
      })
      if (!res.ok) throw new Error((await res.json()).detail)
      setShowStoreMemory(false); setMemoryForm({ content: '', epoch: '', source: 'user_stated' }); setLastEventTime(Date.now())
    } catch (e) { setFormError(e.message) }
    setFormLoading(false)
  }

  const runRecall = async () => {
    if (!recallForm.query.trim()) { setFormError('Enter a recall query.'); return }
    setFormLoading(true); setFormError('')
    try {
      const res = await fetch(`${API_URL}/memories/recall`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workspace: activeWorkspace.name, query: recallForm.query, limit: recallForm.limit })
      })
      if (!res.ok) throw new Error((await res.json()).detail)
      setRecallResults(await res.json())
    } catch (e) { setFormError(e.message) }
    setFormLoading(false)
  }

  const handleJump = async () => {
    setIsJumping(true); setJumpDelta(null)
    try {
      const res = await fetch(`${API_URL}/jump/delta`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workspace: activeWorkspace.name, from_epoch: jumpFrom, to_epoch: jumpTo || undefined })
      })
      setJumpDelta(await res.json())
    } catch (e) { console.error(e) }
    setIsJumping(false)
  }

  // Shared modal close + error reset
  const closeModal = (setter) => { setter(false); setFormError('') }

  // ── Sidebar nav items ─────────────────────────────────────────────────────────
  const navItems = [
    { id: 'hub', label: 'Workspace Hub', icon: <Database size={18} />, color: 'cyan' },
    { id: 'timeline', label: 'Epoch Timeline', icon: <History size={18} />, color: 'cyan', disabled: !activeWorkspace },
    { id: 'jump', label: 'Temporal Jump', icon: <Zap size={18} />, color: 'purple', disabled: !activeWorkspace },
    { id: 'feed', label: 'Live Feed', icon: <Bell size={18} />, color: 'purple' },
  ]

  return (
    <div className="app-container">
      {/* ── Sidebar ─────────────────────────────────────────────────────── */}
      <aside className="sidebar">
        <div>
          <h1 className="text-glow-cyan" style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: '1.4rem' }}>
            <BrainCircuit size={26} color="var(--accent-cyan)" />
            TLCM
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: 4 }}>Temporal Memory Engine</p>
        </div>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 16 }}>
          {navItems.map(item => (
            <button key={item.id}
              className={`glass-panel ${activeTab === item.id ? `text-glow-${item.color}` : ''}`}
              onClick={() => !item.disabled && setActiveTab(item.id)}
              disabled={item.disabled}
              style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 16px', border: activeTab === item.id ? `1px solid var(--accent-${item.color})` : '', opacity: item.disabled ? 0.4 : 1, cursor: item.disabled ? 'not-allowed' : 'pointer' }}>
              {item.icon}{item.label}
            </button>
          ))}
        </nav>

        {/* Active workspace badge */}
        {activeWorkspace && (
          <div style={{ marginTop: 'auto', padding: '14px 16px', background: 'rgba(100,255,218,0.05)', border: '1px solid var(--border-glass)', borderRadius: '10px' }}>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '4px' }}>Active Workspace</p>
            <p className="text-glow-cyan" style={{ color: 'var(--accent-cyan)', fontWeight: 700, fontSize: '0.9rem' }}>{activeWorkspace.name}</p>
            <div style={{ display: 'flex', gap: '8px', marginTop: '12px', flexWrap: 'wrap' }}>
              <button onClick={() => { setShowStoreMemory(true); setFormError('') }}
                style={{ flex: 1, fontSize: '0.75rem', padding: '6px 8px', display: 'flex', alignItems: 'center', gap: 5, justifyContent: 'center' }}>
                <Plus size={12} /> Memory
              </button>
              <button onClick={() => { setShowRecall(true); setFormError(''); setRecallResults(null) }}
                style={{ flex: 1, fontSize: '0.75rem', padding: '6px 8px', display: 'flex', alignItems: 'center', gap: 5, justifyContent: 'center' }}>
                <Search size={12} /> Recall
              </button>
            </div>
          </div>
        )}
      </aside>

      {/* ── Main Content ─────────────────────────────────────────────────────── */}
      <main className="main-content">

        {/* ── Workspace Hub ──────────────────────────────────────────── */}
        {activeTab === 'hub' && (
          <div className="animate-fade-in">
            <header className="page-header">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <h1 className="page-title text-glow-cyan">Workspace Hub</h1>
                  <p className="page-subtitle">Isolated cognitive environments. Each is mathematically incapable of cross-contamination.</p>
                </div>
                <button className="primary" onClick={() => { setShowCreateWs(true); setFormError('') }}
                  style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 20px', whiteSpace: 'nowrap', marginTop: '4px' }}>
                  <Plus size={16} /> New Workspace
                </button>
              </div>
            </header>

            <div className="grid-cards">
              {workspaces.map(ws => (
                <div key={ws.id} className="glass-panel"
                  style={{ cursor: 'pointer', border: activeWorkspace?.id === ws.id ? '1px solid var(--accent-cyan)' : '', transform: activeWorkspace?.id === ws.id ? 'translateY(-4px)' : '' }}
                  onClick={() => { setActiveWorkspace(ws); setActiveTab('timeline') }}>
                  <h3 className={activeWorkspace?.id === ws.id ? 'text-glow-cyan' : ''} style={{ marginBottom: '8px' }}>{ws.name}</h3>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>{ws.description || 'No description'}</p>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 20, paddingTop: 14, borderTop: '1px solid var(--border-glass)' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{new Date(ws.created_at).toLocaleDateString()}</span>
                    <span style={{ background: 'rgba(100,255,218,0.1)', color: 'var(--accent-cyan)', padding: '3px 8px', borderRadius: 4, fontSize: '0.75rem' }}>
                      {ws.memory_count || 0} Memories
                    </span>
                  </div>
                </div>
              ))}
              {workspaces.length === 0 && (
                <div style={{ gridColumn: '1/-1', textAlign: 'center', padding: '60px 20px', color: 'var(--text-muted)' }}>
                  <BrainCircuit size={48} style={{ margin: '0 auto 16px', opacity: 0.3, display: 'block' }} />
                  <p style={{ fontSize: '1.1rem', marginBottom: '8px' }}>No workspaces yet</p>
                  <p style={{ fontSize: '0.85rem' }}>Create your first cognitive environment to begin.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Epoch Timeline ──────────────────────────────────────────── */}
        {activeTab === 'timeline' && activeWorkspace && (
          <div className="animate-fade-in">
            <header className="page-header">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <h1 className="page-title text-glow-cyan">Epoch Timeline</h1>
                  <p className="page-subtitle">Workspace: <strong style={{ color: 'var(--accent-cyan)' }}>{activeWorkspace.name}</strong> · Temporally separated belief states</p>
                </div>
                <button className="primary" onClick={() => { setShowCreateEpoch(true); setFormError('') }}
                  style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 20px', whiteSpace: 'nowrap', marginTop: '4px' }}>
                  <Plus size={16} /> New Epoch
                </button>
              </div>
            </header>

            {epochs.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--text-muted)' }}>
                <History size={48} style={{ margin: '0 auto 16px', opacity: 0.3, display: 'block' }} />
                <p style={{ fontSize: '1.1rem', marginBottom: '8px' }}>No epochs created yet</p>
                <p style={{ fontSize: '0.85rem' }}>Create your first epoch to begin tracking temporal belief states.</p>
              </div>
            ) : (
              <div style={{ maxWidth: 900 }}>
                {epochs.map(epoch => (
                  <div key={epoch.id} className={`memory-node ${!epoch.is_active ? 'historical' : ''}`}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <h3 style={{ color: epoch.is_active ? 'var(--accent-cyan)' : 'var(--text-main)' }}>
                        {epoch.name} {epoch.is_active && <span style={{ fontSize: '0.7rem', background: 'rgba(100,255,218,0.15)', padding: '2px 8px', borderRadius: '20px', marginLeft: '8px' }}>ACTIVE</span>}
                      </h3>
                      {epoch.is_active && (
                        <button onClick={() => { setMemoryForm(f => ({ ...f, epoch: epoch.name })); setShowStoreMemory(true); setFormError('') }}
                          style={{ fontSize: '0.78rem', padding: '5px 12px', display: 'flex', alignItems: 'center', gap: 5 }}>
                          <Plus size={12} /> Add Memory
                        </button>
                      )}
                    </div>
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', margin: '6px 0 14px' }}>{epoch.description}</p>
                    <EpochMemories workspace={activeWorkspace} epoch={epoch} lastEventTime={lastEventTime} />
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Temporal Jump ───────────────────────────────────────────── */}
        {activeTab === 'jump' && activeWorkspace && (
          <div className="animate-fade-in">
            <header className="page-header">
              <h1 className="page-title text-glow-purple" style={{ color: 'var(--accent-purple)' }}>Temporal Delta Laboratory</h1>
              <p className="page-subtitle">Compute the exact mathematical divergence between two world-states. Pure Python set operations — no hallucination.</p>
            </header>

            <div className="glass-panel" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 28 }}>
              <div>
                <label style={{ display: 'block', marginBottom: 8, color: 'var(--accent-cyan)', fontSize: '0.85rem' }}>Origin Epoch</label>
                <select value={jumpFrom} onChange={e => setJumpFrom(e.target.value)}>
                  <option value="">Select origin state…</option>
                  {epochs.map(e => <option key={e.id} value={e.name}>{e.name}</option>)}
                </select>
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: 8, color: 'var(--accent-purple)', fontSize: '0.85rem' }}>Target Epoch</label>
                <select value={jumpTo} onChange={e => setJumpTo(e.target.value)}>
                  <option value="">Current State (Now)</option>
                  {epochs.map(e => <option key={e.id} value={e.name}>{e.name}</option>)}
                </select>
              </div>
            </div>

            <button className="primary"
              style={{ width: '100%', padding: 14, fontSize: '1rem', display: 'flex', justifyContent: 'center', gap: 12, background: 'var(--accent-purple)', borderColor: 'var(--accent-purple)', boxShadow: '0 0 15px rgba(199,125,255,0.3)' }}
              onClick={handleJump} disabled={!jumpFrom || isJumping}>
              <Activity size={20} className={isJumping ? 'jump-spin' : ''} />
              {isJumping ? 'Reconstructing Mathematical Delta…' : 'INITIATE TEMPORAL JUMP'}
            </button>

            {jumpDelta && (
              <div className="animate-fade-in" style={{ marginTop: 40 }}>
                <h2 style={{ textAlign: 'center', color: 'var(--accent-purple)', marginBottom: '28px' }}>Calculated Delta</h2>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
                  {[
                    { label: 'Continuities', key: 'continuities', color: '#4ade80', prefix: '' },
                    { label: 'New Beliefs', key: 'additions', color: 'var(--accent-cyan)', prefix: '+ ' },
                    { label: 'Evolutions', key: 'evolutions', color: 'var(--accent-purple)', prefix: '' },
                  ].map(({ label, key, color, prefix }) => (
                    <div key={key} className="glass-panel" style={{ borderTop: `3px solid ${color}` }}>
                      <h3 style={{ color, marginBottom: 14, fontSize: '0.9rem' }}>
                        {label} ({(jumpDelta[key] || []).length})
                      </h3>
                      {(jumpDelta[key] || []).map((item, i) => (
                        <div key={i} style={{ fontSize: '0.82rem', color: 'var(--text-muted)', borderBottom: '1px solid var(--border-glass)', paddingBottom: 8, marginBottom: 8 }}>
                          {key === 'evolutions' ? (
                            <>
                              <div style={{ textDecoration: 'line-through', color: '#888' }}>{item.from?.content}</div>
                              <div style={{ color: 'var(--accent-purple)', fontSize: '0.72rem', margin: '3px 0' }}>↓ {item.reason}</div>
                              <div style={{ color: 'var(--text-main)' }}>{item.to?.content}</div>
                            </>
                          ) : `${prefix}${item.content}`}
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Live Feed ────────────────────────────────────────────────── */}
        {activeTab === 'feed' && (
          <div className="animate-fade-in">
            <header className="page-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--accent-cyan)', boxShadow: '0 0 8px var(--accent-cyan)', animation: 'pulse 2s infinite' }} />
                <h1 className="page-title text-glow-cyan" style={{ fontSize: '2rem' }}>Live Memory Feed</h1>
              </div>
              <p className="page-subtitle">Real-time SSE events from the async ingestion bus — memory_stored, reconsolidation_boost, proactive_context.</p>
            </header>
            <div className="glass-panel" style={{ maxWidth: 800 }}>
              <ActivityFeed events={feedEvents} />
            </div>
          </div>
        )}
      </main>

      {/* ── Create Workspace Modal ─────────────────────────────────────────── */}
      {showCreateWs && (
        <Modal title="Create New Workspace" onClose={() => closeModal(setShowCreateWs)}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div>
              <label style={{ display: 'block', marginBottom: 6, color: 'var(--accent-cyan)', fontSize: '0.85rem' }}>Workspace Name *</label>
              <input id="ws-name-input" value={wsForm.name} onChange={e => setWsForm(f => ({ ...f, name: e.target.value }))}
                placeholder="e.g. agi_research_2026" onKeyDown={e => e.key === 'Enter' && createWorkspace()} autoFocus />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: 6, color: 'var(--text-muted)', fontSize: '0.85rem' }}>Description</label>
              <input value={wsForm.description} onChange={e => setWsForm(f => ({ ...f, description: e.target.value }))}
                placeholder="What cognitive context does this workspace represent?" />
            </div>
            {formError && <p style={{ color: '#da6b6b', fontSize: '0.85rem' }}>{formError}</p>}
            <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
              <button className="primary" onClick={createWorkspace} disabled={formLoading} style={{ flex: 1, padding: 12 }}>
                {formLoading ? 'Creating…' : 'Create Workspace'}
              </button>
              <button onClick={() => closeModal(setShowCreateWs)} style={{ padding: 12, minWidth: 80 }}>Cancel</button>
            </div>
          </div>
        </Modal>
      )}

      {/* ── Create Epoch Modal ─────────────────────────────────────────────── */}
      {showCreateEpoch && activeWorkspace && (
        <Modal title={`New Epoch in "${activeWorkspace.name}"`} onClose={() => closeModal(setShowCreateEpoch)}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div>
              <label style={{ display: 'block', marginBottom: 6, color: 'var(--accent-cyan)', fontSize: '0.85rem' }}>Epoch Name *</label>
              <input value={epochForm.name} onChange={e => setEpochForm(f => ({ ...f, name: e.target.value }))}
                placeholder="e.g. phase_1, pre_launch, q3_2026" autoFocus />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: 6, color: 'var(--text-muted)', fontSize: '0.85rem' }}>Description</label>
              <input value={epochForm.description} onChange={e => setEpochForm(f => ({ ...f, description: e.target.value }))}
                placeholder="What temporal phase does this epoch represent?" />
            </div>
            {formError && <p style={{ color: '#da6b6b', fontSize: '0.85rem' }}>{formError}</p>}
            <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
              <button className="primary" onClick={createEpoch} disabled={formLoading} style={{ flex: 1, padding: 12 }}>
                {formLoading ? 'Creating…' : 'Create Epoch'}
              </button>
              <button onClick={() => closeModal(setShowCreateEpoch)} style={{ padding: 12, minWidth: 80 }}>Cancel</button>
            </div>
          </div>
        </Modal>
      )}

      {/* ── Store Memory Modal ─────────────────────────────────────────────── */}
      {showStoreMemory && activeWorkspace && (
        <Modal title={`Store Memory in "${activeWorkspace.name}"`} onClose={() => closeModal(setShowStoreMemory)}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div>
              <label style={{ display: 'block', marginBottom: 6, color: 'var(--accent-cyan)', fontSize: '0.85rem' }}>Memory Content *</label>
              <textarea value={memoryForm.content} onChange={e => setMemoryForm(f => ({ ...f, content: e.target.value }))}
                placeholder="What should be remembered? State it as a clear fact or observation."
                style={{ minHeight: 100, resize: 'vertical' }} autoFocus />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: 6, color: 'var(--text-muted)', fontSize: '0.85rem' }}>Epoch (optional)</label>
              <select value={memoryForm.epoch} onChange={e => setMemoryForm(f => ({ ...f, epoch: e.target.value }))}>
                <option value="">Auto — Active Epoch</option>
                {epochs.map(e => <option key={e.id} value={e.name}>{e.name}</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: 6, color: 'var(--text-muted)', fontSize: '0.85rem' }}>Source</label>
              <select value={memoryForm.source} onChange={e => setMemoryForm(f => ({ ...f, source: e.target.value }))}>
                <option value="user_stated">user_stated</option>
                <option value="observed">observed</option>
                <option value="inferred">inferred</option>
                <option value="external_data">external_data</option>
              </select>
            </div>
            {formError && <p style={{ color: '#da6b6b', fontSize: '0.85rem' }}>{formError}</p>}
            <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
              <button className="primary" onClick={storeMemory} disabled={formLoading} style={{ flex: 1, padding: 12 }}>
                {formLoading ? 'Storing…' : 'Store Memory'}
              </button>
              <button onClick={() => closeModal(setShowStoreMemory)} style={{ padding: 12, minWidth: 80 }}>Cancel</button>
            </div>
          </div>
        </Modal>
      )}

      {/* ── Recall Memory Modal ────────────────────────────────────────────── */}
      {showRecall && activeWorkspace && (
        <Modal title={`Recall from "${activeWorkspace.name}"`} onClose={() => closeModal(setShowRecall)}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div>
              <label style={{ display: 'block', marginBottom: 6, color: 'var(--accent-cyan)', fontSize: '0.85rem' }}>Semantic Query *</label>
              <input value={recallForm.query} onChange={e => setRecallForm(f => ({ ...f, query: e.target.value }))}
                placeholder="What do you want to recall? Use natural language." autoFocus
                onKeyDown={e => e.key === 'Enter' && runRecall()} />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: 6, color: 'var(--text-muted)', fontSize: '0.85rem' }}>Results Limit</label>
              <select value={recallForm.limit} onChange={e => setRecallForm(f => ({ ...f, limit: parseInt(e.target.value) }))}>
                {[3, 5, 10, 20].map(n => <option key={n} value={n}>{n} results</option>)}
              </select>
            </div>
            {formError && <p style={{ color: '#da6b6b', fontSize: '0.85rem' }}>{formError}</p>}
            <button className="primary" onClick={runRecall} disabled={formLoading} style={{ padding: 12 }}>
              {formLoading ? 'Searching…' : 'Search Memories'}
            </button>

            {recallResults && (
              <div style={{ marginTop: 8, borderTop: '1px solid var(--border-glass)', paddingTop: 16 }}>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginBottom: 12 }}>{recallResults.length} result(s)</p>
                {recallResults.length === 0 && <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>No relevant memories found.</p>}
                {recallResults.map(m => (
                  <div key={m.id} style={{ padding: '10px 14px', border: '1px solid var(--border-glass)', borderRadius: 8, marginBottom: 8, background: 'rgba(100,255,218,0.03)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>#{m.id.substring(0, 8)}</span>
                      <span style={{ fontSize: '0.72rem', color: 'var(--accent-cyan)' }}>C: {(m.confidence * 100).toFixed(0)}%</span>
                    </div>
                    <p style={{ fontSize: '0.875rem', color: 'var(--text-main)' }}>{m.content}</p>
                    <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 4 }}>{m.epoch || 'unknown epoch'} · {m.source}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Modal>
      )}
    </div>
  )
}

export default App
