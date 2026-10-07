import { useEffect, useState, type FormEvent, useRef } from 'react';
import { createRoot } from 'react-dom/client';
import Markdown from 'react-markdown';
import './style.css';

type Evidence = { id: string; path: string; line: number; text: string };
type Result = { readme: string; revision: string; evidence: Evidence[]; grounding: string; metrics: { loaded_files: number; skipped_files: number; chunks: number; total_ms: number; retrieval_ms: number } };
type ChatMessage = { role: 'user' | 'assistant'; content: string };
type Citation = { source_id: string; path: string; line_start: number };
type ChatResponse = { answer: string; related: boolean; citations: Citation[] };

function App() {
  const [url, setUrl] = useState('');
  const [rerank, setRerank] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<Result | null>(null);
  const [raw, setRaw] = useState(false);
  
  // Chat state
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatBusy, setChatBusy] = useState(false);
  const [chatError, setChatError] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory, chatBusy]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(''); setResult(null); setBusy(true); setChatHistory([]);
    try {
      const response = await fetch('/api/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ repo_url: url.trim(), rerank }) });
      const text = await response.text();
      let data;
      try {
        data = JSON.parse(text);
      } catch (e) {
        throw new Error(`Server returned non-JSON response (${response.status}). Are you missing an environment variable?`);
      }
      if (!response.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : 'The request could not be processed. Check the repository URL.');
      setResult(data); setRaw(false);
    } catch (err) { setError(err instanceof Error ? err.message : 'Generation failed. Please retry.'); }
    finally { setBusy(false); }
  }

  async function sendChatMessage(event?: FormEvent) {
    if (event) event.preventDefault();
    const msg = chatInput.trim();
    if (!msg || chatBusy || !url.trim()) return;
    
    setChatInput('');
    setChatError('');
    setChatBusy(true);
    
    const newHistory = [...chatHistory, { role: 'user', content: msg } as ChatMessage];
    setChatHistory(newHistory);
    
    try {
      const response = await fetch('/api/chat', { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ 
          repository_url: url.trim(), 
          message: msg, 
          conversation: chatHistory 
        }) 
      });
      const text = await response.text();
      let data;
      try {
        data = JSON.parse(text);
      } catch (e) {
        throw new Error(`Server returned non-JSON response (${response.status}).`);
      }
      if (!response.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : 'Chat request failed.');
      
      let answerText = data.answer;
      if (data.citations && data.citations.length > 0) {
        answerText += '\n\n**Sources:**\n' + data.citations.map((c: Citation) => `- [${c.source_id}] ${c.path}:${c.line_start}`).join('\n');
      }
      
      setChatHistory([...newHistory, { role: 'assistant', content: answerText }]);
    } catch (err) { 
      setChatError(err instanceof Error ? err.message : 'Chat failed.');
      setChatHistory([...newHistory, { role: 'assistant', content: 'An error occurred. Please try again.' }]);
    } finally { 
      setChatBusy(false); 
    }
  }

  function download() {
    if (!result) return;
    const blob = URL.createObjectURL(new Blob([result.readme], { type: 'text/markdown;charset=utf-8' }));
    const link = document.createElement('a'); link.href = blob; link.download = 'README.md'; link.click();
    setTimeout(() => URL.revokeObjectURL(blob), 1000);
  }

  return <>
    <header><a className="brand" href="/" aria-label="RepoScribe home"><span className="mark" aria-hidden="true">R/</span>RepoScribe</a><span className="header-note">REPOSITORY WORKSPACE</span></header>
    <main>
      <section className="intro"><p className="eyebrow">CODE → DOCUMENTATION</p><h1>A clearer starting point<br/>for your next README.</h1><p className="lede">Turn a public repository into documentation grounded in its files. Inspect the sources, then make it yours.</p></section>
      <div className="workspace">
        <aside><form onSubmit={submit}>
          <div className="section-label"><span>01</span><h2>Choose a repository</h2></div>
          <label htmlFor="repository">Public GitHub URL</label>
          <input id="repository" type="url" required maxLength={200} placeholder="https://github.com/owner/repository" value={url} onChange={e => setUrl(e.target.value)} disabled={busy}/>
          <label className="checkbox"><input type="checkbox" checked={rerank} onChange={e => setRerank(e.target.checked)} disabled={busy}/>Try experimental reranking</label>
          <button className="primary" disabled={busy || !url.trim()}>{busy ? 'Generating README…' : 'Generate README →'}</button>
          {error && <p className="error" role="alert">{error}</p>}
        </form>
        </aside>
        <div className="document-container" style={{ display: 'flex', flexDirection: 'column', gap: '2rem', flex: 1 }}>
          <section className="document" aria-busy={busy} aria-label="README output">
            <div className="document-bar"><div className="section-label"><span>02</span><h2>README.md</h2></div>{result && <button onClick={download}>Download ↓</button>}</div>
            {busy ? <div className="empty" role="status"><span className="document-icon" aria-hidden="true">…</span><h3>Reading your repository</h3><p>Loading files, retrieving evidence, and drafting your README. This can take a few minutes.</p></div> : result ? <>
              <div className="metrics"><span>{result.metrics.loaded_files} files read</span><span>{result.metrics.chunks} chunks</span><span>{(result.metrics.total_ms / 1000).toFixed(1)}s total</span><span>{result.metrics.retrieval_ms.toFixed(1)}ms retrieval</span></div>
              <div className="view-switch" aria-label="Document view"><button aria-pressed={!raw} onClick={() => setRaw(false)}>Preview</button><button aria-pressed={raw} onClick={() => setRaw(true)}>Markdown</button></div>
              {raw ? <pre className="raw">{result.readme}</pre> : <article className="markdown"><Markdown skipHtml components={{ img: ({ alt }) => <span>{alt || 'Image omitted'}</span> }}>{result.readme}</Markdown></article>}
              <details className="evidence"><summary>Evidence · {result.evidence.length} passages</summary><p className="hint">{result.grounding} {result.metrics.skipped_files} files skipped. Commit: {result.revision}</p>{result.evidence.map(e => <details key={e.id}><summary>[{e.id}] {e.path}:{e.line}</summary><pre>{e.text}</pre></details>)}</details>
            </> : <div className="empty"><span className="document-icon" aria-hidden="true">≡</span><h3>Your documentation starts here</h3><p>Add a repository on the left. Your README, source references, and generation metrics will appear here.</p><span className="empty-label">MARKDOWN OUTPUT · TRACEABLE SOURCES</span></div>}
          </section>

          {result && (
            <section className="document chat-section" aria-label="Chat with Repository" style={{ display: 'flex', flexDirection: 'column', height: '500px' }}>
              <div className="document-bar"><div className="section-label"><span>03</span><h2>Chat with Repository</h2></div></div>
              <div className="chat-messages" style={{ flex: 1, overflowY: 'auto', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '1rem', background: '#fcfcfc' }}>
                {chatHistory.length === 0 ? (
                  <div className="empty" style={{ margin: 'auto', opacity: 0.7 }}>
                    <p>Ask anything about this repository's code, architecture, technologies, or setup.</p>
                  </div>
                ) : (
                  chatHistory.map((msg, i) => (
                    <div key={i} className={`chat-message ${msg.role}`} style={{ alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '80%', padding: '0.8rem 1rem', borderRadius: '8px', background: msg.role === 'user' ? '#f0f0eb' : '#fff', border: '1px solid #e2e2dd' }}>
                      <p style={{ margin: '0 0 0.5rem 0', fontWeight: 600, fontSize: '0.85rem', color: msg.role === 'user' ? '#245747' : '#333' }}>{msg.role === 'user' ? 'User' : 'RepoScribe'}</p>
                      <div className="markdown" style={{ fontSize: '0.95rem', margin: 0 }}><Markdown>{msg.content}</Markdown></div>
                    </div>
                  ))
                )}
                {chatBusy && <div className="chat-message assistant" style={{ alignSelf: 'flex-start', padding: '0.8rem 1rem', borderRadius: '8px', background: '#fff', border: '1px solid #e2e2dd' }}><em>Thinking...</em></div>}
                <div ref={messagesEndRef} />
              </div>
              <form onSubmit={sendChatMessage} style={{ display: 'flex', gap: '0.5rem', padding: '1rem', borderTop: '1px solid #e2e2dd', background: '#fff' }}>
                <textarea 
                  value={chatInput} 
                  onChange={e => setChatInput(e.target.value)} 
                  onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChatMessage(); } }}
                  placeholder="Ask anything about this repository..." 
                  disabled={chatBusy}
                  style={{ flex: 1, resize: 'none', padding: '0.6rem', borderRadius: '6px', border: '1px solid #ccc' }}
                  rows={2}
                />
                <button type="submit" disabled={chatBusy || !chatInput.trim()} className="primary" style={{ alignSelf: 'flex-end' }}>Send</button>
              </form>
              {chatError && <p className="error" style={{ padding: '0 1rem 1rem' }}>{chatError}</p>}
            </section>
          )}
        </div>
      </div>
      <footer><span>RepoScribe</span><span>Read the code. Keep the context.</span></footer>
    </main>
  </>;
}

createRoot(document.getElementById('root')!).render(<App/>);
