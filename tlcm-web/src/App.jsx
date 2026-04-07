import { useState, useEffect } from 'react'
import { BrainCircuit, Database, History, Zap, Activity } from 'lucide-react'

const API_URL = "http://127.0.0.1:8000/api"

function App() {
  const [workspaces, setWorkspaces] = useState([])
  const [activeWorkspace, setActiveWorkspace] = useState(null)
  const [epochs, setEpochs] = useState([])
  const [activeTab, setActiveTab] = useState('hub')
  
  // Jump State
  const [jumpFrom, setJumpFrom] = useState('')
  const [jumpTo, setJumpTo] = useState('')
  const [jumpResult, setJumpResult] = useState(null)
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
    try {
      const res = await fetch(`${API_URL}/jump/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workspace: activeWorkspace.name,
          from_epoch: jumpFrom,
          to_epoch: jumpTo || undefined
        })
      })
      const data = await res.json()
      setJumpResult(data.result)
    } catch (e) {
      setJumpResult("Error connecting to Memory Engine. Ensure FastAPI is running.")
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
            <Zap size={20} />
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
                  style={{ cursor: 'pointer', border: activeWorkspace?.id === ws.id ? '1px solid var(--accent-cyan)' : '' }}
                  onClick={() => setActiveWorkspace(ws)}
                >
                  <h3 className="text-glow-cyan">{ws.name}</h3>
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
              <p className="page-subtitle">All memories organized by temporal phase.</p>
            </header>

            <div style={{ maxWidth: 800 }}>
              {epochs.map(epoch => (
                <div key={epoch.id} className={`memory-node ${!epoch.is_active ? 'historical' : ''}`}>
                  <h3 style={{ color: epoch.is_active ? 'var(--accent-cyan)' : 'var(--text-muted)' }}>
                    {epoch.name} {epoch.is_active && '(Active)'}
                  </h3>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: 16 }}>{epoch.description}</p>
                  
                  <div className="glass-panel" style={{ padding: 16 }}>
                    <p style={{ color: 'var(--text-muted)', fontStyle: 'italic', fontSize: '0.9rem' }}>
                      {epoch.memory_count} memories recorded in this epoch.
                    </p>
                    {/* In a real app we would map memories here */}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Temporal Jump Tab */}
        {activeTab === 'jump' && activeWorkspace && (
          <div className="animate-fade-in">
            <header className="page-header">
              <h1 className="page-title text-glow-purple" style={{ color: 'var(--accent-purple)' }}>Temporal Jump Laboratory</h1>
              <p className="page-subtitle">Reconstruct past world-states. Measure the delta.</p>
            </header>

            <div className="glass-panel" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 32 }}>
              <div>
                <label style={{ display: 'block', marginBottom: 8, color: 'var(--accent-cyan)' }}>Jump From State (Origin Epoch)</label>
                <select value={jumpFrom} onChange={e => setJumpFrom(e.target.value)}>
                  <option value="">Select an Epoch...</option>
                  {epochs.map(e => <option key={e.id} value={e.name}>{e.name}</option>)}
                </select>
              </div>
              
              <div>
                <label style={{ display: 'block', marginBottom: 8, color: 'var(--accent-purple)' }}>Jump To State (Target Epoch)</label>
                <select value={jumpTo} onChange={e => setJumpTo(e.target.value)}>
                  <option value="">Current State (Now)</option>
                  {epochs.map(e => <option key={e.id} value={e.name}>{e.name}</option>)}
                </select>
              </div>
            </div>

            <button 
              className="primary" 
              style={{ width: '100%', padding: 16, fontSize: '1.1rem', display: 'flex', justifyContent: 'center', gap: 12, background: 'var(--accent-purple)', borderColor: 'var(--accent-purple)' }}
              onClick={handleJump}
              disabled={!jumpFrom || isJumping}
            >
              <Activity size={24} />
              {isJumping ? "Reconstructing Time-State..." : "INITIATE TEMPORAL JUMP"}
            </button>

            {jumpResult && (
              <div className="glass-panel" style={{ marginTop: 32, border: '1px solid var(--accent-purple)', background: 'rgba(199, 125, 255, 0.05)' }}>
                <h3 className="text-glow-purple" style={{ marginBottom: 16 }}>Temporal Delta Analysis</h3>
                <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>
                  {jumpResult}
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
