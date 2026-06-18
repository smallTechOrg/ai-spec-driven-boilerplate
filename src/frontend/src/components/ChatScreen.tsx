import { useState, useRef, useEffect } from 'react';
import { askQuestion, type SessionInfo } from '../api';

interface Step {
  action: string;
  result: string;
  is_error: boolean;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  steps?: Step[];
  iterationCount?: number;
}

interface Props {
  session: SessionInfo;
  onReset: () => void;
}

export function ChatScreen({ session, onReset }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set());
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const send = async () => {
    const q = input.trim();
    if (!q || loading) return;
    setInput('');
    setError('');
    setMessages(prev => [...prev, { role: 'user', content: q }]);
    setLoading(true);
    try {
      const resp = await askQuestion(session.session_id, q);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: resp.answer,
        steps: resp.reasoning_trace,
        iterationCount: resp.iteration_count,
      }]);
    } catch (e: any) {
      setError(e.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  const toggleSteps = (i: number) => {
    setExpandedSteps(prev => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
  };

  return (
    <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
      {/* Sidebar */}
      <div style={{
        width: '240px', background: '#1e293b', color: '#fff',
        padding: '20px 16px', display: 'flex', flexDirection: 'column', flexShrink: 0,
      }}>
        <div style={{ fontSize: '18px', fontWeight: 700, marginBottom: '4px' }}>DataChat</div>
        <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '24px' }}>AI Data Assistant</div>

        <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>
          Current file
        </div>
        <div style={{ fontSize: '13px', fontWeight: 600, wordBreak: 'break-all' }}>{session.filename}</div>
        <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>{session.row_count.toLocaleString()} rows</div>

        <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', marginTop: '20px', marginBottom: '6px' }}>
          Columns ({session.column_names.length})
        </div>
        <div style={{ fontSize: '12px', color: '#cbd5e1', lineHeight: '1.8', overflow: 'auto', flex: 1 }}>
          {session.column_names.map(c => <div key={c} style={{ fontFamily: 'monospace' }}>{c}</div>)}
        </div>

        <button
          onClick={onReset}
          style={{
            marginTop: '16px', padding: '8px', background: '#334155',
            color: '#cbd5e1', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '13px',
          }}
        >
          Upload new file
        </button>
      </div>

      {/* Chat area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px 32px' }}>
          {messages.length === 0 && (
            <div style={{ textAlign: 'center', color: '#999', marginTop: '60px' }}>
              <p style={{ fontSize: '20px' }}>👋</p>
              <p style={{ marginTop: '8px' }}>Ask anything about <strong>{session.filename}</strong></p>
              <p style={{ fontSize: '13px', color: '#bbb', marginTop: '4px' }}>
                e.g. "What is the average value?", "Show the top 5 rows", "Any outliers?"
              </p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} style={{ marginBottom: '20px' }}>
              <div style={{
                display: 'flex',
                justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
              }}>
                <div style={{
                  maxWidth: '72%',
                  background: msg.role === 'user' ? '#2563eb' : '#fff',
                  color: msg.role === 'user' ? '#fff' : '#222',
                  borderRadius: msg.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                  padding: '12px 16px',
                  fontSize: '14px',
                  lineHeight: '1.6',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
                  whiteSpace: 'pre-wrap',
                }}>
                  {msg.content}
                </div>
              </div>

              {msg.role === 'assistant' && msg.steps && msg.steps.length > 0 && (
                <div style={{ marginTop: '6px', paddingLeft: '4px' }}>
                  <button
                    onClick={() => toggleSteps(i)}
                    style={{
                      background: 'none', border: 'none', cursor: 'pointer',
                      fontSize: '12px', color: '#64748b', padding: '2px 4px',
                    }}
                  >
                    {expandedSteps.has(i) ? '▼' : '▶'} {msg.steps.length} reasoning step{msg.steps.length !== 1 ? 's' : ''}
                  </button>

                  {expandedSteps.has(i) && (
                    <div style={{
                      marginTop: '6px', background: '#f8fafc', border: '1px solid #e2e8f0',
                      borderRadius: '8px', padding: '12px', fontSize: '12px', fontFamily: 'monospace',
                    }}>
                      {msg.steps.map((step, j) => (
                        <div key={j} style={{ marginBottom: '10px' }}>
                          <div style={{ color: '#2563eb', fontWeight: 600 }}>
                            Step {j + 1}: df.{step.action}
                          </div>
                          <div style={{
                            color: step.is_error ? '#dc2626' : '#374151',
                            marginTop: '2px', whiteSpace: 'pre-wrap', wordBreak: 'break-all',
                            maxHeight: '120px', overflow: 'auto',
                          }}>
                            {step.result.slice(0, 500)}{step.result.length > 500 ? '…' : ''}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div style={{ color: '#888', fontSize: '14px', display: 'flex', gap: '6px', alignItems: 'center' }}>
              <span>Analysing</span>
              <span style={{ animation: 'pulse 1.4s infinite' }}>…</span>
            </div>
          )}

          {error && (
            <div style={{ color: '#dc2626', fontSize: '13px', padding: '8px 12px', background: '#fef2f2', borderRadius: '6px' }}>
              {error}
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input bar */}
        <div style={{
          padding: '16px 32px', background: '#fff', borderTop: '1px solid #e5e7eb',
          display: 'flex', gap: '10px',
        }}>
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
            placeholder="Ask a question about your data…"
            disabled={loading}
            style={{
              flex: 1, padding: '10px 14px', border: '1px solid #d1d5db',
              borderRadius: '8px', fontSize: '14px', outline: 'none',
            }}
          />
          <button
            onClick={send}
            disabled={loading || !input.trim()}
            style={{
              padding: '10px 20px', background: loading ? '#93c5fd' : '#2563eb',
              color: '#fff', border: 'none', borderRadius: '8px',
              cursor: loading ? 'not-allowed' : 'pointer', fontSize: '14px', fontWeight: 600,
            }}
          >
            {loading ? '…' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  );
}
