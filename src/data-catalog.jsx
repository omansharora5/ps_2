import React, { useEffect, useState } from 'react';
import { ArrowDownToLine, ArrowUpRight, Check, Database, Download, RefreshCw } from 'lucide-react';
import { serviceJSON } from './service-client';
import './exploration.css';

const bytesLabel = value => value >= 1e6 ? `${(value / 1e6).toFixed(1)} MB` : `${(value / 1e3).toFixed(1)} KB`;
export default function DataCatalog() {
  const [catalog, setCatalog] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState('');
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  const active = jobs.some(job => ['queued', 'running'].includes(job.status));
  useEffect(() => {
    const controller = new AbortController();
    let timer;
    async function refresh() {
      try {
        const [next, nextJobs] = await Promise.all([serviceJSON('data/catalog', { signal: controller.signal }), serviceJSON('data/jobs', { signal: controller.signal })]);
        setCatalog(next); setJobs(nextJobs.jobs); setError(''); setLoading(false);
        if (nextJobs.jobs.some(job => ['queued', 'running'].includes(job.status))) timer = setTimeout(refresh, 2000);
      } catch (error) { if (error.name !== 'AbortError') { setError(error.message); setLoading(false); } }
    }
    refresh();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [retry]);
  async function collect(id) {
    setSubmitting(id); setError('');
    try {
      const job = await serviceJSON(`data/collections/${encodeURIComponent(id)}`, { body: {} });
      setJobs(previous => [job, ...previous.filter(value => value.id !== job.id)]);
      setRetry(value => value + 1);
    } catch (error) { setError(error.message); }
    finally { setSubmitting(''); }
  }
  return <section className="data-catalog" aria-labelledby="catalog-heading">
    <div className="section-heading"><div><p className="eyebrow">SOURCE FILES, NOT ASSUMPTIONS</p><h2 id="catalog-heading">The data collection desk</h2></div><button className="button secondary" onClick={() => setRetry(value => value + 1)} disabled={loading}><RefreshCw size={16} aria-hidden="true" />Refresh catalogue</button></div>
    <p className="catalog-intro">See what is actually on disk, download a source file, or collect an approved starter pack from the local service.</p>
    {loading && <p className="catalog-loading" role="status">Reading the source catalogue…</p>}
    {error && <div className="error-box" role="alert">{error}</div>}
    {catalog && <><div className="scope-banner"><Database size={20} aria-hidden="true" /><span><strong>Starter corpus · not training-ready.</strong> {catalog.scope}</span></div>
      <div className="collection-grid">{catalog.collections.map(collection => <article className="panel collection-card" key={collection.id} data-testid={`collection-${collection.id}`}><div className="collection-card-top"><span className={`collection-status status-${collection.status}`}>{collection.status === 'available' ? <Check size={14} aria-hidden="true" /> : <Database size={14} aria-hidden="true" />}{collection.status}</span><span>{bytesLabel(collection.bytes)}</span></div><h3>{collection.name}</h3><p>{collection.local_file_count} of {collection.file_count} files available locally</p><button className="button primary" onClick={() => collect(collection.id)} disabled={!catalog.collection_enabled || active || Boolean(submitting)}><Download size={16} aria-hidden="true" />{submitting === collection.id ? 'Starting collection…' : `Collect ${collection.name}`}</button><details><summary>Inspect source files</summary><ul className="collection-files">{collection.files.map(file => <li key={file.id}><strong>{file.name}</strong><span>{file.provider} · {file.format} · {file.local_status}</span><p>{file.not_training_ready_reason}</p><div><a href={file.source_url} target="_blank" rel="noreferrer">Source<ArrowUpRight size={13} aria-hidden="true" /></a>{file.local_status === 'present_size_matches' && <a href={file.download_url || `/api/data/files/${encodeURIComponent(file.id)}`} download>Download<ArrowDownToLine size={13} aria-hidden="true" /></a>}</div></li>)}</ul></details></article>)}</div>
      <p className="collection-policy">{catalog.collection_enabled ? 'Collection is enabled for direct local access. Each job reports its outcome and retrieval log for this server session.' : 'Collection is disabled on this server. A local operator can enable the bounded collector; available files can still be inspected and downloaded.'} {catalog.collection_policy} {catalog.integrity_note}</p>
      {jobs.length > 0 && <section className="panel collection-jobs"><div className="panel-heading"><h3>Collection jobs</h3><span>{active ? 'Updating every 2 seconds' : 'Recorded outcomes'}</span></div>{jobs.slice(0, 6).map(job => <details key={job.id}><summary><span>{job.collection_id}</span><strong>{job.status}</strong><time>{job.created_at}</time></summary>{job.error && <p className="job-error">{job.error}</p>}<pre>{Array.isArray(job.log) ? job.log.join('\n') : job.log || 'No log entries yet.'}</pre></details>)}</section>}
      <details className="panel source-register"><summary>Provider register and access requirements</summary><div className="table-scroll"><table><thead><tr><th>Provider / source</th><th>Access</th><th>Current status</th></tr></thead><tbody>{catalog.sources.map(source => <tr key={source.id}><td><a href={source.source_url} target="_blank" rel="noreferrer">{source.name}<ArrowUpRight size={12} aria-hidden="true" /></a><small>{source.provider}</small>{source.api_url && <a className="provider-api-link" href={source.api_url} target="_blank" rel="noreferrer">API / access docs<ArrowUpRight size={12} aria-hidden="true" /></a>}</td><td>{source.access}</td><td>{source.status}<small>{source.notes}</small></td></tr>)}</tbody></table></div></details>
    </>}
  </section>;
}
