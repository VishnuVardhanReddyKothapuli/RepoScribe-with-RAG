import { useEffect, useState, type FormEvent } from 'react';
import { createRoot } from 'react-dom/client';
import Markdown from 'react-markdown';
import './style.css';

type Evidence = { id: string; path: string; line: number; text: string };
type Result = { readme: string; revision: string; evidence: Evidence[]; grounding: string; metrics: { loaded_files: number; skipped_files: number; chunks: number; total_ms: number; retrieval_ms: number } };

function App() {
  const [url, setUrl] = useState('');
  const [rerank, setRerank] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<Result | null>(null);
  const [raw, setRaw] = useState(false);
  const [health, setHealth] = useState('Connecting to local API…');
  const [ready, setReady] = useState(false);

  useEffect(() => {
    fetch('/api/health').then(async response => {
      if (!response.ok) throw new Error();
      const data = await response.json();
      setReady(data.ready);
      setHealth(data.ready ? `Ready · ${data.model}` : 'Setup needed · add GOOGLE_API_KEY to the server .env file');
    }).catch(() => setHealth('API offline · start the Python server on port 8000'));
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(''); setResult(null); setBusy(true);
    try {
      const response = await fetch('/api/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ repo_url: url.trim(), rerank }) });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'The request could not be processed. Check the repository URL.');
      setResult(data); setRaw(false);
    } catch (err) { setError(err instanceof Error ? err.message : 'Generation failed. Please retry.'); }
    finally { setBusy(false); }
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
          <input id="repository" type="url" required maxLength={200} placeholder="https://github.com/owner/repository" value={url} onChange={e => setUrl(e.target.value)} disabled={busy} aria-describedby="repo-hint"/>
          <p id="repo-hint" className="hint">Public repositories only. Repository code is never executed.</p>
          <label className="checkbox"><input type="checkbox" checked={rerank} onChange={e => setRerank(e.target.checked)} disabled={busy}/>Try experimental reranking</label>
          <p className="hint">Reorders retrieval candidates by query coverage. Off by default while we measure its impact.</p>
          <button className="primary" disabled={busy || !url.trim() || !ready}>{busy ? 'Generating README…' : 'Generate README →'}</button>
          <p className="connection" role="status">{health}</p>
          {error && <p className="error" role="alert">{error}</p>}
        </form>
        <div className="notes"><h3>Built from evidence</h3><p>Each generated claim should cite a source. Open the evidence panel to check it against the repository.</p><p>Missing details are omitted. Always review commands and setup instructions before publishing.</p></div>
        </aside>
        <section className="document" aria-busy={busy} aria-label="README output">
          <div className="document-bar"><div className="section-label"><span>02</span><h2>README.md</h2></div>{result && <button onClick={download}>Download ↓</button>}</div>
          {busy ? <div className="empty" role="status"><span className="document-icon" aria-hidden="true">…</span><h3>Reading your repository</h3><p>Loading files, retrieving evidence, and drafting your README. This can take a few minutes.</p></div> : result ? <>
            <div className="metrics"><span>{result.metrics.loaded_files} files read</span><span>{result.metrics.chunks} chunks</span><span>{(result.metrics.total_ms / 1000).toFixed(1)}s total</span><span>{result.metrics.retrieval_ms.toFixed(1)}ms retrieval</span></div>
            <div className="view-switch" aria-label="Document view"><button aria-pressed={!raw} onClick={() => setRaw(false)}>Preview</button><button aria-pressed={raw} onClick={() => setRaw(true)}>Markdown</button></div>
            {raw ? <pre className="raw">{result.readme}</pre> : <article className="markdown"><Markdown skipHtml components={{ img: ({ alt }) => <span>{alt || 'Image omitted'}</span> }}>{result.readme}</Markdown></article>}
            <details className="evidence"><summary>Evidence · {result.evidence.length} passages</summary><p className="hint">{result.grounding} {result.metrics.skipped_files} files skipped. Commit: {result.revision}</p>{result.evidence.map(e => <details key={e.id}><summary>[{e.id}] {e.path}:{e.line}</summary><pre>{e.text}</pre></details>)}</details>
          </> : <div className="empty"><span className="document-icon" aria-hidden="true">≡</span><h3>Your documentation starts here</h3><p>Add a repository on the left. Your README, source references, and generation metrics will appear here.</p><span className="empty-label">MARKDOWN OUTPUT · TRACEABLE SOURCES</span></div>}
        </section>
      </div>
      <footer><span>RepoScribe</span><span>Read the code. Keep the context.</span></footer>
    </main>
  </>;
}

createRoot(document.getElementById('root')!).render(<App/>);
