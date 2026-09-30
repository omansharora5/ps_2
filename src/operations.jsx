import React, { useEffect, useRef, useState } from 'react';
import { ArrowDownToLine, ArrowRight, CheckCircle2, Database, FlaskConical, RefreshCw, Timer, TriangleAlert } from 'lucide-react';
import { serviceJSON } from './service-client';
import './operations.css';

const labels = { starter_audit: 'Source integrity', radar_replay: 'Observed radar evaluation', train_candidate: 'Model candidate' };
const statusLabel = { queued: 'Queued', running: 'Running', succeeded: 'Completed', failed: 'Failed', cancelled: 'Cancelled' };
const stageLabel = value => (value || 'waiting').replaceAll('_', ' ');
const timeLabel = value => value ? new Date(value).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : 'Not recorded';
const score = value => typeof value === 'number' && Number.isFinite(value) ? value.toFixed(5) : 'Unavailable';

function Result({ job, writable, busy, act }) {
  const training = job.summary?.mode === 'training_candidate' ? job.summary : null;
  const audit = job.summary?.mode === 'starter_integrity_audit' ? job.summary : null;
  const radar = job.summary?.mode === 'observed_radar_replay' ? job.summary : null;
  return <section className="panel operations-result" aria-labelledby="operation-result-title">
    <div className="panel-heading"><div><p className="eyebrow">RECORDED RESULT</p><h2 id="operation-result-title">{labels[job.kind]}</h2></div><span className={'operation-status ' + job.status}>{statusLabel[job.status]}</span></div>
    <dl className="operations-details"><div><dt>Stage</dt><dd>{stageLabel(job.stage)}</dd></div><div><dt>Data scope</dt><dd>{job.scope.replaceAll('_', ' ')}</dd></div><div><dt>Last change</dt><dd>{timeLabel(job.updated_at)}</dd></div><div><dt>Attempt</dt><dd>{job.attempt} of 3 maximum</dd></div></dl>
    <p className="operations-id">Record {job.id}</p>
    {job.error && <p role="alert" className="operations-error-text">{job.error}</p>}
    {training && <div className="operations-science"><div><h3>{training.recommendation === 'retain_baseline' ? 'The baseline remains stronger.' : 'Candidate recorded for research review.'}</h3><p>Lower Brier scores are better. These are development results on the stated dataset; no model has been promoted.</p></div><div className="table-scroll"><table><thead><tr><th>Forecast</th><th>Brier score ↓</th></tr></thead><tbody><tr><td>Raw candidate</td><td>{score(training.raw_brier)}</td></tr><tr><td>Calibrated candidate</td><td>{score(training.calibrated_brier)}</td></tr><tr><td>Training climatology baseline</td><td>{score(training.baseline_brier)}</td></tr></tbody></table></div><p className="panel-footnote">{training.test_event_count} held-out event groups. Pixel counts are not independent storm counts.</p></div>}
    {audit && <div className="operations-science"><h3>{audit.verified} of {audit.checked} source files verified</h3><p>{audit.problems ? 'Some files need attention. Review the audit before using them.' : 'Recorded file sizes and hashes match the downloaded provider manifests.'}</p><p className="panel-footnote">These historical samples cover different places and dates. Passing this check does not make them a matched training dataset.</p></div>}
    {radar && <div className="operations-science"><h3>Observed radar, +{radar.horizon_minutes} minutes</h3><p>Compare predicted radar echoes with the later observed frame on shared valid coverage. This experiment has no lightning labels.</p><div className="table-scroll"><table><thead><tr><th>Method</th><th>CSI ↑</th><th>POD ↑</th><th>FAR ↓</th></tr></thead><tbody>{[['Optical flow', radar.metrics.selected], ['Persistence', radar.metrics.persistence]].map(([name, metrics]) => <tr key={name}><td>{name}</td><td>{score(metrics.csi)}</td><td>{score(metrics.pod)}</td><td>{score(metrics.far)}</td></tr>)}</tbody></table></div><p className="panel-footnote">{radar.time_note}. A single case does not establish general superiority.</p></div>}
    {job.summary && <details><summary>Inspect recorded result fields</summary><pre>{JSON.stringify(job.summary, null, 2)}</pre></details>}
    <div className="operations-actions">{job.artifacts.map(artifact => <a key={artifact.id} className="button secondary" href={artifact.download_url} download><ArrowDownToLine size={16} aria-hidden="true" />{artifact.name}</a>)}
      {['failed', 'cancelled'].includes(job.status) && job.attempt < 3 && <button className="button secondary" disabled={!writable || busy} onClick={() => void act('operations/jobs/' + job.id + '/retry', { expected_attempt: job.attempt }, 'retry')}>Retry cancelled or failed work</button>}
      {['queued', 'running'].includes(job.status) && <button className="button secondary" disabled={!writable || busy} onClick={() => void act('operations/jobs/' + job.id + '/cancel', {}, 'cancel')}>Cancel experiment</button>}
    </div>
    {job.status === 'cancelled' && <p className="panel-footnote">This job cannot publish a result. An in-progress numerical call may finish before the worker returns idle.</p>}
  </section>;
}

export default function Operations() {
  const [state, setState] = useState(null);
  const [error, setError] = useState('');
  const [actionError, setActionError] = useState('');
  const [notice, setNotice] = useState('');
  const [pending, setPending] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [fetchedAt, setFetchedAt] = useState(null);
  const [kind, setKind] = useState('starter_audit');
  const [datasetId, setDatasetId] = useState('');
  const [selectedId, setSelectedId] = useState(null);
  const [selectedJob, setSelectedJob] = useState(null);
  const selection = useRef(null);
  const request = useRef(null);
  const alive = useRef(false);
  async function refresh() {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setRefreshing(true);
    try {
      const data = await serviceJSON('operations/state', { signal: controller.signal });
      const requestedId = selection.current;
      const detail = requestedId ? data.jobs?.find(job => job.id === requestedId) ||
        await serviceJSON('operations/jobs/' + requestedId, { signal: controller.signal }) : null;
      if (controller.signal.aborted || !alive.current) return;
      if (data.schema_version !== 1 || !Array.isArray(data.jobs) || !Array.isArray(data.datasets)) throw new Error('The research service returned an unsupported response.');
      if (selection.current === requestedId) setSelectedJob(detail);
      setState(data); setError(''); setFetchedAt(new Date().toISOString());
    } catch (failure) {
      if (failure.name !== 'AbortError' && alive.current) setError(failure.message);
    } finally {
      if (!controller.signal.aborted && alive.current) setRefreshing(false);
    }
  }
  useEffect(() => {
    alive.current = true;
    void refresh();
    const interval = setInterval(() => { if (document.visibilityState === 'visible') void refresh(); }, 5000);
    return () => { alive.current = false; clearInterval(interval); request.current?.abort(); };
  }, []);
  function selectJob(job) {
    selection.current = job.id;
    setSelectedId(job.id);
    setSelectedJob(job);
  }
  async function act(path, body, action) {
    if (pending) return;
    setPending(action); setActionError(''); setNotice('');
    try {
      const result = await serviceJSON(path, { body });
      if (!alive.current) return;
      if (action === 'submit') {
        selectJob(result);
        setNotice('Request recorded. Repeating the same experiment opens its existing job.');
      } else if (action === 'prepare') {
        setDatasetId(result.id); setKind('train_candidate');
        setNotice('Eight generated example events are ready. They test the training workflow, not Indian weather accuracy.');
      } else setNotice('Change recorded.');
      await refresh();
    } catch (failure) {
      if (alive.current) setActionError(failure.message);
    } finally {
      if (alive.current) setPending('');
    }
  }
  const selected = selectedId ? selectedJob : state?.jobs[0];
  const chosenDataset = state?.datasets.find(dataset => dataset.id === datasetId);
  const writable = Boolean(state?.writes_enabled && !error);
  const busy = Boolean(pending);
  return <div className="operations-page">
    <section className="panel operations-lead" aria-labelledby="operations-purpose">
      <div><p className="eyebrow">THE RESEARCH LOOP</p><h2 id="operations-purpose">Make the next experiment count.</h2><p>Check the inputs, run a recorded experiment, then inspect the result. Completed work and model quality are shown separately.</p></div>
      <div className="operations-contact"><span className={'operation-status ' + (state?.worker.available ? 'succeeded' : 'queued')}><Timer size={15} aria-hidden="true" />{state?.worker.available ? 'Worker recently connected' : 'Waiting for worker contact'}</span><small>Last contact: {timeLabel(state?.worker.last_seen_at)}</small><a href="/research/OPERATIONS_GUIDE.md" download>Setup and architecture <ArrowDownToLine size={14} aria-hidden="true" /></a></div>
    </section>
    <ol className="operations-flow" aria-label="Research workflow">
      <li><Database size={22} aria-hidden="true" /><div><strong>1. Know the data</strong><span>Source files, event groups and coverage</span></div></li>
      <li><FlaskConical size={22} aria-hidden="true" /><div><strong>2. Run one experiment</strong><span>Saved identity, stages and attempts</span></div></li>
      <li><CheckCircle2 size={22} aria-hidden="true" /><div><strong>3. Review the evidence</strong><span>Held-out scores, baseline and limitations</span></div></li>
    </ol>
    <div className="operations-refresh"><span>{fetchedAt ? 'Updated ' + timeLabel(fetchedAt) : 'Loading research operations…'}{error && fetchedAt ? ' · saved screen state is out of date' : ''}</span><button className="button secondary" onClick={() => void refresh()} disabled={refreshing}><RefreshCw size={16} aria-hidden="true" />{refreshing ? 'Refreshing…' : 'Refresh operations'}</button></div>
    {error && <div role="alert" className="operations-error"><TriangleAlert size={20} aria-hidden="true" /><div><strong>Operations could not refresh.</strong><p>{error}</p>{state && <p>The last fetched records remain visible. Actions are disabled until reconnection.</p>}</div></div>}
    {!state && !error && <div className="panel" role="status">Connecting to the job and dataset records…</div>}
    {state && <>
      <div className="operations-layout">
        <section className="panel operations-form" aria-labelledby="next-experiment">
          <p className="eyebrow">NEXT ACTION</p><h2 id="next-experiment">Choose an experiment</h2>
          {!state.writes_enabled && <p className="operations-note">This connection can inspect research work. Starting jobs requires an enabled local operations server.</p>}
          <label htmlFor="operation-recipe">Experiment</label><select id="operation-recipe" value={kind} onChange={event => { setKind(event.target.value); setNotice(''); }} disabled={busy}>{state.recipes.map(recipe => <option key={recipe.id} value={recipe.id}>{recipe.title}</option>)}</select>
          <p className="panel-footnote">{state.recipes.find(recipe => recipe.id === kind)?.description}</p>
          {kind === 'train_candidate' && <><label htmlFor="operation-dataset">Frozen dataset</label><select id="operation-dataset" value={datasetId} onChange={event => setDatasetId(event.target.value)} disabled={busy}><option value="">Select registered episodes</option>{state.datasets.map(dataset => <option key={dataset.id} value={dataset.id}>{dataset.name} · {dataset.event_count} events</option>)}</select>
            {chosenDataset && <div className="operations-note"><strong>{chosenDataset.scope.replaceAll('_', ' ')}</strong><p>{chosenDataset.target}</p><p>{chosenDataset.learning_eligible ? 'Eligible for the observed-data learning check.' : chosenDataset.readiness_reasons.join(' ')}</p></div>}
            {state.datasets.length === 0 && <p className="panel-footnote">No episodes are registered. Prepare the generated example to test this workflow, or register matched observations using the guide.</p>}
          </>}
          <button className="button primary w-full" disabled={!writable || busy || (kind === 'train_candidate' && !chosenDataset)} onClick={() => void act('operations/jobs', { kind, ...(kind === 'train_candidate' ? { dataset_id: datasetId } : {}) }, 'submit')}>{pending === 'submit' ? 'Recording request…' : 'Queue experiment'}<ArrowRight size={17} aria-hidden="true" /></button>
          {!state.worker.available && <p className="panel-footnote">Queued work stays saved until the dedicated worker starts. Refreshing this page does not execute it.</p>}
          <div className="operations-form-divider" /><h3>Try the training flow</h3><p className="panel-footnote">Create a small, explicitly generated dataset with separate training, validation, calibration and test events.</p>
          <button className="button secondary" disabled={!writable || busy} onClick={() => void act('operations/datasets/demo', {}, 'prepare')}>{pending === 'prepare' ? 'Preparing episodes…' : 'Prepare example episodes'}</button>
          {notice && <p role="status" className="operations-success">{notice}</p>}
          {actionError && <p role="alert" className="operations-error-text">{actionError}</p>}
        </section>
        <section className="panel operations-history" aria-labelledby="recorded-experiments">
          <div className="panel-heading"><div><p className="eyebrow">DURABLE RECORDS</p><h2 id="recorded-experiments">Recent experiments</h2></div><span className="operations-count">{state.jobs.length}</span></div>
          {state.jobs.length === 0 ? <div className="empty-state"><FlaskConical size={28} aria-hidden="true" /><strong>No experiment recorded yet</strong><p>Start with source integrity to verify the files already downloaded.</p></div> : <ul className="operations-job-list">{state.jobs.map(job => <li key={job.id}><button className={'operations-job ' + (selected?.id === job.id ? 'selected' : '')} aria-pressed={selected?.id === job.id} onClick={() => selectJob(job)}><span><strong>{labels[job.kind]}</strong><small>{timeLabel(job.created_at)} · attempt {job.attempt}</small></span><span className={'operation-status ' + job.status}>{statusLabel[job.status]}</span></button></li>)}</ul>}
        </section>
      </div>
      {selected && <Result job={selected} writable={writable} busy={busy} act={act} />}
      <section className="panel operations-learning" aria-labelledby="daily-learning">
        <div><p className="eyebrow">CONTROLLED LEARNING</p><h2 id="daily-learning">New evidence, then a new candidate.</h2><p>The daily check looks for newly admitted observed event groups with mature labels. It does not train again on an unchanged dataset or replace the active forecast model.</p><p><strong>{state.learning.enabled ? 'Daily checks enabled' : 'Daily checks paused'}</strong> · {stageLabel(state.learning.status)}</p><p className="panel-footnote">{state.learning.note}</p><p className="panel-footnote">Last check: {timeLabel(state.learning.last_checked_at)}</p></div>
        <button className="button secondary" disabled={!writable || busy} onClick={() => void act('operations/learning', { enabled: !state.learning.enabled }, 'learning')}>{state.learning.enabled ? 'Pause daily checks' : 'Enable daily checks'}</button>
      </section>
      <div className="operations-references"><strong>Methods behind this workflow</strong>{state.research.map(item => <a key={item.url} href={item.url} download>{item.title}<ArrowDownToLine size={14} aria-hidden="true" /></a>)}</div>
    </>}
  </div>;
}
