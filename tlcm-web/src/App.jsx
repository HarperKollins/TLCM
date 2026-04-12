import { useState, useEffect } from 'react'
import { BrainCircuit, Database, History, Zap, Activity } from 'lucide-react'

const API_URL = "http://127.0.0.1:8000/api"

const MemoryTree = ({ history }) => {
  return (
    <div className="animate-fade-in" style={{ padding: '20px', background: 'var(--bg-obsidian)', border: '1px solid var(--border-glass)', borderRadius: '8px', marginTop: '16px' }}>
      <h4 style={{ color: 'var(--accent-purple)', marginBottom: '16px' }}>Belief Arc (Version Evolution)</h4>
      {history.map((mem, idx) => (
        <div key={mem.id} style={{ display: 'flex', alignItems: 'flex-start' }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginRight: '16px' }}>
            <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: 'var(--accent-cyan)', boxShadow: '0 0 8px var(--accent-cyan)' }}></div>
            {idx !== history.length - 1 && <div style={{ width: '2px', minHeight: '40px', height: '100%', background: 'var(--border-glass)', alignSelf: 'stretch' }}></div>}
          </div>
          <div style={{ paddingBottom: idx !== history.length - 1 ? '16px' : '0' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Version {mem.version} • {new Date(mem.created_at).toLocaleString()}
            </div>
            <p style={{ color: 'var(--text-main)', fontSize: '0.95rem' }}>{mem.content}</p>
            {mem.update_reason && (
              <div style={{ fontSize: '0.85rem', fontStyle: 'italic', color: 'var(--accent-purple)', marginTop: '8px', paddingLeft: '12px', borderLeft: '2px solid var(--accent-purple)' }}>
                {mem.update_reason}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

const EpochMemories = ({ workspace, epoch }) => {
  const [memories, setMemories] = useState([])
  const [activeMemoryHistory, setActiveMemoryHistory] = useState(null)

  useEffect(() => {
    fetch(`${API_URL}/memories/workspace/${workspace.name}/epoch/${epoch.name}`)
      .then(res => res.json())
      .then(data => setMemories(data))
      .catch(e => console.error(e))
  }, [workspace, epoch])

  const loadHistory = async (mem) => {
    if (activeMemoryHistory && activeMemoryHistory[activeMemoryHistory.length-1].id === mem.id) {
      setActiveMemoryHistory(null)
      return
    }
    try {
      const res = await fetch(`${API_URL}/memories/${mem.id}/history`)
      const data = await res.json()
      setActiveMemoryHistory(data)
    } catch(e) {
      console.error(e)
    }
  }

  if (memories.length === 0) {
    return <div style={{ padding: '16px', color: 'var(--text-muted)' }}>No memories in this epoch yet.</div>
  }

  return (
    <div style={{ marginTop: '16px' }}>
      {memories.map(m => (
        <div key={m.id} className="glass-panel hover-glow" style={{ marginBottom: '16px', padding: '20px', cursor: 'pointer' }} onClick={() => loadHistory(m)}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Node #{m.id.substring(0,8)}</span>
            <div style={{ display: 'flex', gap: '12px' }}>
              <span style={{ color: m.confidence > 0.8 ? 'var(--accent-cyan)' : 'var(--text-muted)', fontSize: '0.8rem' }}>Confidence: {(m.confidence * 100).toFixed(0)}%</span>
              <span style={{ color: 'var(--accent-purple)', fontSize: '0.8rem', fontWeight: 'bold' }}>v{m.version}</span>
            </div>
          </div>
          <p style={{ fontSize: '1rem', lineHeight: '1.5' }}>{m.content}</p>
          
          {activeMemoryHistory && activeMemoryHistory[activeMemoryHistory.length-1].id === m.id && (
             <MemoryTree history={activeMemoryHistory} />
          )}
        </div>
      ))}
    </div>
  )
}

function App() {
  const [workspaces, setWorkspaces] = useState([])
  const [activeWorkspace, setActiveWorkspace] = useState(null)
  const [epochs, setEpochs] = useState([])
  const [activeTab, setActiveTab] = useState('hub')
  
  // Jump State
  const [jumpFrom, setJumpFrom] = useState('')
  const [jumpTo, setJumpTo] = useState('')
  const [jumpDelta, setJumpDelta] = useState(null)
  const [isJumping, setIsJumping] = useState(false)

  // Fetch workspaces on load
  useEffect(() => {
    fetch(`${API_URL}/workspaces/`)
      .then(res => res.json())
      .then(data => setWorkspaces(data))
      .catch(err => console.error("API not available:", err))
  }, [])

  // Fetch epochs when workspace changes
  useEffect(() => {
    if (activeWorkspace) {
      fetch(`${API_URL}/epochs/${activeWorkspace.name}`)
        .then(res => res.json())
        .then(data => setEpochs(data))
    }
  }, [activeWorkspace])

  const handleJump = async () => {
    setIsJumping(true)
    setJumpDelta(null)
    try {
      const res = await fetch(`${API_URL}/jump/delta`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workspace: activeWorkspace.name,
          from_epoch: jumpFrom,
          to_epoch: jumpTo || undefined
        })
      })
      const data = await res.json()
      setJumpDelta(data)
    } catch (e) {
      console.error(e)
    }
    setIsJumping(false)
  }

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div>
          <h1 className="text-glow-cyan" style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: '1.5rem' }}>
            <BrainCircuit size={28} color="var(--accent-cyan)" />
            TLCM
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: 8 }}>Temporal Memory Engine</p>
        </div>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 24 }}>
          <button 
            className={`glass-panel ${activeTab === 'hub' ? 'active text-glow-cyan' : ''}`}
            onClick={() => setActiveTab('hub')}
            style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 16, border: activeTab === 'hub' ? '1px solid var(--accent-cyan)' : '' }}
          >
            <Database size={20} />
            Workspace Hub
          </button>
          
          <button 
            className={`glass-panel ${activeTab === 'timeline' ? 'active text-glow-cyan' : ''}`}
            onClick={() => setActiveTab('timeline')}
            style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 16, border: activeTab === 'timeline' ? '1px solid var(--accent-cyan)' : '' }}
            disabled={!activeWorkspace}
          >
            <History size={20} />
            Epoch Timeline
          </button>

          <button 
            className={`glass-panel ${activeTab === 'jump' ? 'active text-glow-purple' : ''}`}
            onClick={() => setActiveTab('jump')}
            style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 16, border: activeTab === 'jump' ? '1px solid var(--accent-purple)' : '' }}
            disabled={!activeWorkspace}
          >
            <Zap size={20} color={activeWorkspace ? "var(--accent-purple)" : "var(--text-muted)"} />
            Temporal Jump
          </button>
        </nav>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        
        {/* Workspace Hub Tab */}
        {activeTab === 'hub' && (
          <div className="animate-fade-in">
            <header className="page-header">
              <h1 className="page-title text-glow-cyan">Workspace Hub</h1>
              <p className="page-subtitle">Isolated cognitive environments.</p>
            </header>

            <div className="grid-cards">
              {workspaces.map(ws => (
                <div 
                  key={ws.id} 
                  className="glass-panel" 
                  style={{ cursor: 'pointer', border: activeWorkspace?.id === ws.id ? '1px solid var(--accent-cyan)' : '', transform: activeWorkspace?.id === ws.id ? 'translateY(-4px)' : '' }}
                  onClick={() => setActiveWorkspace(ws)}
                >
                  <h3 className={activeWorkspace?.id === ws.id ? "text-glow-cyan" : ""}>{ws.name}</h3>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', margin: '12px 0' }}>{ws.description || 'No description'}</p>
                  
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 24, paddingTop: 16, borderTop: '1px solid var(--border-glass)' }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Created {new Date(ws.created_at).toLocaleDateString()}</span>
                    <span style={{ background: 'rgba(100,255,218,0.1)', color: 'var(--accent-cyan)', padding: '4px 8px', borderRadius: 4, fontSize: '0.8rem' }}>
                      {ws.memory_count || 0} Memories
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Epoch Timeline Tab */}
        {activeTab === 'timeline' && activeWorkspace && (
          <div className="animate-fade-in">
            <header className="page-header">
              <h1 className="page-title text-glow-cyan">Epoch Timeline: {activeWorkspace.name}</h1>
              <p className="page-subtitle">Interactive memory mapping separated by temporal phase.</p>
            </header>

            <div style={{ maxWidth: 900 }}>
              {epochs.map(epoch => (
                <div key={epoch.id} className={`memory-node ${!epoch.is_active ? 'historical' : ''}`}>
                  <h3 style={{ color: epoch.is_active ? 'var(--accent-cyan)' : 'var(--text-main)' }}>
                    {epoch.name} {epoch.is_active && '(Active State)'}
                  </h3>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: 16 }}>{epoch.description}</p>
                  
                  <EpochMemories workspace={activeWorkspace} epoch={epoch} />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Temporal Jump Tab */}
        {activeTab === 'jump' && activeWorkspace && (
          <div className="animate-fade-in">
            <header className="page-header">
              <h1 className="page-title text-glow-purple">Temporal Delta Laboratory</h1>
              <p className="page-subtitle">Compute the exact mathematical divergence between two world-states.</p>
            </header>

            <div className="glass-panel" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 32 }}>
              <div>
                <label style={{ display: 'block', marginBottom: 8, color: 'var(--accent-cyan)' }}>Origin Epoch</label>
                <select value={jumpFrom} onChange={e => setJumpFrom(e.target.value)}>
                  <option value="">Select Origin State...</option>
                  {epochs.map(e => <option key={e.id} value={e.name}>{e.name}</option>)}
                </select>
              </div>
              
              <div>
                <label style={{ display: 'block', marginBottom: 8, color: 'var(--accent-purple)' }}>Target Epoch</label>
                <select value={jumpTo} onChange={e => setJumpTo(e.target.value)}>
                  <option value="">Current State (Now)</option>
                  {epochs.map(e => <option key={e.id} value={e.name}>{e.name}</option>)}
                </select>
              </div>
            </div>

            <button 
              className="primary" 
              style={{ width: '100%', padding: 16, fontSize: '1.1rem', display: 'flex', justifyContent: 'center', gap: 12, background: 'var(--accent-purple)', borderColor: 'var(--accent-purple)', boxShadow: '0 0 15px rgba(199, 125, 255, 0.4)' }}
              onClick={handleJump}
              disabled={!jumpFrom || isJumping}
            >
              <Activity size={24} className={isJumping ? "jump-spin" : ""} />
              {isJumping ? "Reconstructing Mathematical Delta..." : "INITIATE TEMPORAL JUMP"}
            </button>

            {jumpDelta && (
              <div className="animate-fade-in" style={{ marginTop: 48, display: 'flex', flexDirection: 'column', gap: '24px' }}>
                <h2 className="text-glow-purple" style={{ textAlign: 'center', color: 'var(--accent-purple)' }}>Calculated Delta</h2>
                
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
                  {/* Continuities */}
                  <div className="glass-panel" style={{ borderTop: '4px solid #4ade80' }}>
                    <h3 style={{ color: '#4ade80', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{width: 8, height: 8, borderRadius: '50%', background: '#4ade80'}}></div>
                      Continuities ({jumpDelta.continuities.length})
                    </h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {jumpDelta.continuities.map(m => (
                        <div key={m.id} style={{ fontSize: '0.85rem', color: 'var(--text-muted)', borderBottom: '1px solid var(--border-glass)', paddingBottom: '8px' }}>
                          {m.content}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Additions */}
                  <div className="glass-panel" style={{ borderTop: '4px solid var(--accent-cyan)' }}>
                    <h3 style={{ color: 'var(--accent-cyan)', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{width: 8, height: 8, borderRadius: '50%', background: 'var(--accent-cyan)'}}></div>
                      New Beliefs ({jumpDelta.additions.length})
                    </h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {jumpDelta.additions.map(m => (
                        <div key={m.id} style={{ fontSize: '0.85rem', color: 'var(--text-main)', borderBottom: '1px solid var(--border-glass)', paddingBottom: '8px' }}>
                          + {m.content}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Evolutions */}
                  <div className="glass-panel" style={{ borderTop: '4px solid var(--accent-purple)' }}>
                    <h3 style={{ color: 'var(--accent-purple)', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{width: 8, height: 8, borderRadius: '50%', background: 'var(--accent-purple)'}}></div>
                      Evolutions ({jumpDelta.evolutions.length})
                    </h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                      {jumpDelta.evolutions.map((ev, i) => (
                         <div key={i} style={{ borderBottom: '1px solid var(--border-glass)', paddingBottom: '12px' }}>
                           <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textDecoration: 'line-through' }}>{ev.from.content}</div>
                           <div style={{ margin: '4px 0', color: 'var(--accent-purple)', fontSize: '0.75rem' }}>↓ {ev.reason}</div>
                           <div style={{ fontSize: '0.85rem', color: 'var(--text-main)' }}>{ev.to.content}</div>
                         </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

      </main>
    </div>
  )
}

export default App
