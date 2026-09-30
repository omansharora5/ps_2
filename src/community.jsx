import React, { useEffect, useRef, useState } from 'react';
import { Check, CloudRain, Database, RefreshCw, ShieldCheck } from 'lucide-react';
import { LANGUAGES, t } from '../shared/translations';
import { communityRequest, installationId, INSTALLATION_KEY, parseCommunityState, parseReceipt, parseReport, parseSavedReport, REPORT_KEY, reportUUID } from '../shared/community-protocol';
import './community.css';

const answerKeys = { yes: 'communityYes', no: 'communityNo', unsure: 'communityUnsure' };
const words = value => typeof value === 'string' ? value.replaceAll('_', ' ') : 'Unavailable';
const score = value => typeof value === 'number' && Number.isFinite(value) ? value.toFixed(3) : 'Unavailable';
const probability = value => typeof value === 'number' && value >= 0 && value <= 1 ? `${Math.round(value * 100)}%` : 'Unknown';
const list = value => Array.isArray(value) ? value : [];

function EvidenceCard({ evidence, submitted }) {
  return <section className="panel community-card" aria-labelledby="local-evidence-heading">
    <div className="community-card-title"><ShieldCheck aria-hidden="true" size={21} /><h2 id="local-evidence-heading">What supports the forecast?</h2></div>
    <p className="community-status">{words(evidence.status)} · {words(evidence.confidence)}</p>
    <dl className="community-facts"><div><dt>Rain / lightning probability</dt><dd>{submitted ? `${probability(evidence.rain_probability)} / ${probability(evidence.lightning_probability)}` : 'Not shown before an observation is submitted.'}</dd></div><div><dt>Rain onset</dt><dd>{submitted && evidence.onset_interval ? JSON.stringify(evidence.onset_interval) : 'Unknown — no verified onset interval'}</dd></div><div><dt>Heavy rain ends</dt><dd>{submitted && typeof evidence.heavy_rain_end === 'string' ? evidence.heavy_rain_end : 'Unknown'}</dd></div></dl>
    {list(evidence.reasons).length > 0 && <ul className="community-reasons">{evidence.reasons.map((reason, i) => <li key={i}>{String(reason)}</li>)}</ul>}
    <h3>Sensor age and coverage</h3>
    {list(evidence.sensors).length ? <ul className="community-sensors">{evidence.sensors.map((sensor, index) => <li key={sensor.id ?? index}><div><strong>{sensor.name ?? sensor.id}</strong><span>{words(sensor.status)}</span></div><p>{Number.isFinite(sensor.age_minutes) && sensor.age_minutes >= 0 ? `${sensor.age_minutes.toFixed(1)} min old` : 'Age unknown'}{sensor.observed_at_utc && ` · ${sensor.observed_at_utc}`}</p><p>{sensor.note}</p></li>)}</ul> : <p>No matched sensor observations are available.</p>}
    <details><summary>Echo path and radar frames</summary>{submitted && list(evidence.tracks).length ? <pre className="community-json">{JSON.stringify(evidence.tracks, null, 2)}</pre> : <p>No observed storm track is available for this cell. A path will appear only with traceable observations.</p>}</details>
  </section>;
}

function Metrics({ metrics, caption }) {
  return <div className="table-scroll"><table><caption>{caption}</caption><thead><tr><th scope="col">POD</th><th scope="col">FAR</th><th scope="col">CSI</th><th scope="col">Brier</th><th scope="col">Cases</th></tr></thead><tbody><tr>{['pod', 'far', 'csi', 'brier'].map(key => <td key={key}>{score(metrics[key])}</td>)}<td>{metrics.case_count ?? 'Unavailable'}</td></tr></tbody></table></div>;
}

function Scorecard({ card }) {
  const metrics = card.metrics;
  const bins = list(metrics?.reliability).filter(bin => bin.count > 0 && Number.isFinite(bin.mean_probability) && Number.isFinite(bin.observed_frequency));
  return <section className="panel community-card" aria-labelledby="monthly-scorecard-heading"><h2 id="monthly-scorecard-heading">Monthly public scorecard</h2>
    {metrics ? <><p>{card.model_id} · {card.hazard} · {card.month}</p><Metrics metrics={metrics} caption="Published observations and frozen predictions" />
      <p>Events: {metrics.event_count ?? 'Unavailable'} · Publication cutoff: {card.publication_cutoff ?? 'Unavailable'}</p>
      {bins.length ? <><svg className="community-reliability" viewBox="0 0 280 240" role="img" aria-label="Reliability: predicted probability on horizontal axis, observed frequency on vertical axis"><path d="M35 15V205H255 M35 205L235 5" fill="none" stroke="#82929a" strokeDasharray="4 4" />{bins.map((bin, i) => <circle key={i} cx={35 + bin.mean_probability * 200} cy={205 - bin.observed_frequency * 200} r="5" fill="#17685e" />)}<text x="45" y="232">Predicted probability (0–1)</text><text x="5" y="18">1</text><text x="12" y="207">0</text></svg><details><summary>Reliability values</summary><div className="table-scroll"><table><thead><tr><th>Predicted probability</th><th>Observed frequency</th><th>Count</th></tr></thead><tbody>{bins.map((bin, i) => <tr key={i}><td>{score(bin.mean_probability)}</td><td>{score(bin.observed_frequency)}</td><td>{bin.count}</td></tr>)}</tbody></table></div></details></> : <p>No populated reliability bins are published.</p>}
      {card.comparison?.model && card.comparison?.comparator ? <><Metrics metrics={card.comparison.model} caption={`Our model · same ${card.comparison.matched_cases} cases`} /><Metrics metrics={card.comparison.comparator} caption={`${card.comparison.name ?? 'Comparator'} · identical cases`} /></> : <p>IMD comparison unavailable: no matched, comparable bulletin cohort is published.</p>}
    </> : <div className="community-empty"><p><strong>No verified monthly scores yet.</strong></p><p>{card.reason ?? 'No eligible observed test cases are published.'}</p><p>POD, FAR, CSI and reliability will appear when frozen predictions have covered outcomes. An empty scorecard is not zero error.</p></div>}
  </section>;
}

function OperatorReview({ enabled, refresh }) {
  const [reason, setReason] = useState(''), [url, setUrl] = useState(''), [decision, setDecision] = useState('reject');
  const [busy, setBusy] = useState(false), [message, setMessage] = useState(''), [error, setError] = useState('');
  const [queue, setQueue] = useState(null), [selected, setSelected] = useState('');
  const candidate = queue?.find(item => `${item.cell_id}/${item.window_start_utc}` === selected);
  async function load() {
    setBusy(true); setError(''); setQueue(null); setSelected('');
    try { const result = await communityRequest('', 'review-queue'); if (!Array.isArray(result.windows)) throw new Error('Invalid review queue'); setQueue(result.windows); }
    catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  async function submit(event) {
    event.preventDefault(); if (!candidate) return; setBusy(true); setError(''); setMessage('');
    try {
      await communityRequest('', 'review', { cell_id: candidate.cell_id, window_start_utc: candidate.window_start_utc, expected_revision: candidate.revision, decision, reason, evidence_url: url });
      setMessage('Review recorded for this exact evidence revision.'); setQueue(null); setSelected(''); refresh();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  return <details className="panel community-card"><summary>Local operator review</summary><p>Opening this form does not grant operator access. The server requires an enabled local service. Approval produces reviewed weak evidence, not ground truth.</p><p>Approval needs at least five consenting yes/no reports, 80% agreement and independently checked corroboration. New reports make an earlier review stale.</p><form onSubmit={submit} className="community-form" aria-busy={busy}>
    <button type="button" className="button secondary" onClick={load} disabled={busy || !enabled}>Load private review queue</button>
    {queue && <label>Reporting window<select required value={selected} disabled={busy} onChange={e => { setSelected(e.target.value); setReason(''); setUrl(''); }}><option value="">Choose a window</option>{queue.map(item => <option key={`${item.cell_id}/${item.window_start_utc}`} value={`${item.cell_id}/${item.window_start_utc}`}>{item.cell_id} · {item.window_start_utc}</option>)}</select></label>}
    {queue?.length === 0 && <p>No observation windows are available for review.</p>}
    {candidate && <p>Private counts: yes {candidate.yes}, no {candidate.no}, unsure {candidate.unsure}. Consent: {candidate.consenting_reports}. Review: {words(candidate.review_status)}. {candidate.window_closed ? 'Reporting window is closed.' : `Approval opens after ${candidate.reviewable_after_utc ?? 'late-report cutoff'}.`}</p>}
    <label>Review decision<select value={decision} onChange={e => setDecision(e.target.value)} disabled={busy}><option value="reject">Reject candidate</option><option value="approve">Approve as weak evidence</option></select></label>
    <label>Review reason<textarea required minLength={10} maxLength={1000} value={reason} onChange={e => setReason(e.target.value)} disabled={busy} /></label>
    <label>Independent evidence URL<input type="url" maxLength={1000} required={decision === 'approve'} value={url} onChange={e => setUrl(e.target.value)} disabled={busy} placeholder="https://…" /></label>
    <button className="button secondary" disabled={busy || !enabled || !candidate || (decision === 'approve' && !candidate.window_closed)}>{busy ? 'Recording review…' : 'Record review'}</button>{!enabled && <p>Review writes are disabled until current service evidence is available.</p>}{error && <p role="alert">{error}</p>}{message && <p role="status">{message}</p>}
  </form></details>;
}

export default function Community() {
  const [language, setLanguage] = useState('en'); const copy = key => t(language, key);
  const [cell, setCell] = useState(''), [month, setMonth] = useState(new Date().toISOString().slice(0, 7)), [tick, setTick] = useState(0);
  const [state, setState] = useState(null), [loading, setLoading] = useState(true), [loadError, setLoadError] = useState('');
  const [answer, setAnswer] = useState(''), [here, setHere] = useState(false), [consent, setConsent] = useState(false);
  const [installation, setInstallation] = useState(null), [saved, setSaved] = useState(null), [storageError, setStorageError] = useState(false);
  const [busy, setBusy] = useState(false), [error, setError] = useState(''); const posting = useRef(false);
  useEffect(() => {
    try {
      const id = installationId(localStorage.getItem(INSTALLATION_KEY)); localStorage.setItem(INSTALLATION_KEY, id); setInstallation(id);
      const restored = parseSavedReport(localStorage.getItem(REPORT_KEY)); setSaved(restored);
      if (restored) { setCell(restored.request.cell_id); setAnswer(restored.request.answer); setConsent(restored.request.consent_training); }
    } catch { setStorageError(true); }
  }, []);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setLoadError('');
    communityRequest('', `state?month=${encodeURIComponent(month)}${cell ? `&cell_id=${encodeURIComponent(cell)}` : ''}`, undefined, controller.signal)
      .then(parseCommunityState).then(value => { if (!controller.signal.aborted) { setState(value); setLoading(false); } })
      .catch(e => { if (!controller.signal.aborted) { setLoadError(e.message); setLoading(false); } });
    return () => controller.abort();
  }, [cell, month, tick]);
  const locked = busy || Boolean(saved), submitted = Boolean(saved?.receipt);
  const selected = state?.cells.find(item => item.id === cell);
  async function send(event) {
    event.preventDefault(); if (posting.current || storageError || !installation) return;
    posting.current = true; setBusy(true); setError('');
    try {
      const record = saved ?? { request: parseReport({ request_id: reportUUID(), installation_id: installation, cell_id: cell, answer, observed_at_utc: new Date().toISOString(), consent_training: consent }), receipt: null };
      try { localStorage.setItem(REPORT_KEY, JSON.stringify(record)); } catch { setStorageError(true); return; }
      setSaved(record);
      const receipt = parseReceipt(await communityRequest('', 'reports', record.request));
      const complete = { ...record, receipt }; setSaved(complete);
      try { localStorage.setItem(REPORT_KEY, JSON.stringify(complete)); } catch { setStorageError(true); }
      setTick(value => value + 1);
    } catch (e) { setError(e.message); } finally { posting.current = false; setBusy(false); }
  }
  function reset() {
    try { localStorage.removeItem(REPORT_KEY); setSaved(null); setAnswer(''); setConsent(false); setHere(false); setError(''); }
    catch { setStorageError(true); }
  }
  return <div className="community-page">
    <div className="community-toolbar"><label>{copy('language')}<select aria-label="Report language" value={language} onChange={e => setLanguage(e.target.value)}>{LANGUAGES.map(item => <option value={item.code} key={item.code}>{item.name}</option>)}</select></label><button className="button secondary" onClick={() => setTick(value => value + 1)} disabled={loading}><RefreshCw size={16} aria-hidden="true" />Refresh evidence</button></div>
    {loadError && <p className="community-warning" role="alert">Evidence could not refresh: {loadError}. Sending is disabled until refresh succeeds.</p>}
    <div className="community-grid"><section className="panel community-card" aria-labelledby="community-report-heading" lang={language} dir={language === 'ur' ? 'rtl' : 'ltr'}>
      <div className="community-card-title"><CloudRain size={24} aria-hidden="true" /><h2 id="community-report-heading">{copy('communityTitle')}</h2></div><p>{copy('communityPrivacy')}</p>
      <form className="community-form" onSubmit={send} aria-busy={busy}>
        <label>{copy('communityPlace')}<select value={cell} onChange={e => { setCell(e.target.value); setHere(false); }} required disabled={locked || loading} aria-describedby="community-place-hint"><option value="">—</option>{state?.cells.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label>
        <p id="community-place-hint" className="community-small">{copy('communityPlaceHint')}{selected && ` ${selected.bbox.join(', ')} (west, south, east, north).`}</p>
        <label className="community-check"><input type="checkbox" checked={here} onChange={e => setHere(e.target.checked)} required={!saved} disabled={locked} /><span>{copy('communityHere')}</span></label>
        <fieldset disabled={locked || loading}><legend>{copy('communityQuestion')}</legend><div className="community-answers">{Object.entries(answerKeys).map(([value, key]) => <label key={value}><input type="radio" name="rain-answer" value={value} checked={answer === value} onChange={() => setAnswer(value)} required /><span>{copy(key)}</span></label>)}</div></fieldset>
        <label className="community-check"><input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} disabled={locked} /><span>{copy('communityConsent')}</span></label>
        {saved && <p className="community-small">{copy('communityRestored')} {saved.request.observed_at_utc} · {copy(answerKeys[saved.request.answer])}</p>}
        {storageError && <p role="alert">{copy('communityStorageError')}</p>}
        {error && <p className="community-warning" role="alert">{copy('communityError')} <span lang="en">{error}</span></p>}
        {submitted ? <p className="community-success" role="status"><Check size={18} aria-hidden="true" />{copy('communitySaved')} <span className="community-report-id">{saved.receipt.report_id}</span></p> : <button className="button primary" disabled={busy || loading || !!loadError || storageError || !installation || !state?.enabled || (!saved && (!cell || !answer || !here))}>{copy(busy ? 'communitySending' : saved ? 'retry' : 'communitySend')}</button>}
        {loading && <p role="status">{copy('loading')}</p>}{!loading && state && !state.enabled && <p role="status">{copy('communityDisabled')}</p>}
        {saved && <button type="button" className="button secondary" onClick={reset} disabled={busy}>{copy('communityReset')}</button>}
        <p className="community-small">{copy('communityRetryHint')}</p>
      </form>
    </section>{state && <EvidenceCard evidence={state.evidence_card} submitted={submitted && saved.request.cell_id === state.selected_cell} />}</div>
    {state && <><section className="panel community-card" aria-labelledby="community-aggregate-heading"><h2 id="community-aggregate-heading">{copy('communityAggregate')}</h2><p>{state.cells.find(c => c.id === state.selected_cell)?.name} · {state.prompt.window_start_utc} to {state.prompt.window_end_utc}</p><p className="community-status">Evidence status: {words(state.aggregate.public_status)}</p><p>{copy('communityUnverified')}</p><p className="community-small">Exact vote counts and report identities are withheld publicly. Installation reports cannot establish independent people. Majority agreement does not start automatic model training.</p></section>
      <div className="community-toolbar"><label>Scorecard month<input type="month" value={month} onChange={e => { if (e.target.value) setMonth(e.target.value); }} /></label></div><div className="community-grid"><Scorecard card={state.scorecard} /><section className="panel community-card"><div className="community-card-title"><Database size={21} aria-hidden="true" /><h2>Open benchmark readiness</h2></div><p>{words(state.benchmark.status)}</p><p>{state.benchmark.raw_release_allowed ? 'The publication manifest permits the listed raw files.' : 'Raw dataset release is not permitted yet.'}</p><ul>{list(state.benchmark.blockers).map((reason, i) => <li key={i}>{String(reason)}</li>)}</ul><p>A release needs source rights, matched observations, event-separated splits and a versioned manifest. Public reports alone do not make a radar benchmark.</p></section></div>
      <OperatorReview enabled={state.enabled && !loading && !loadError} refresh={() => setTick(value => value + 1)} />
      <div className="community-toolbar"><a className="button secondary" href="/research/PUBLIC_VERIFICATION_GUIDE.md">Public verification guide</a><a className="button secondary" href="/research/REGIONAL_SCIENCE_GUIDE.md">Regional science guide</a></div></>}
  </div>;
}
