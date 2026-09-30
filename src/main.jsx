import React, { lazy, Suspense, useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Activity, ArrowDownToLine, ArrowRight, BookOpen, Check, ChevronRight, Database, FileText, FlaskConical, Globe2, House, Layers, Map, Menu, Radio, RefreshCw, ScanLine, ShieldCheck, Smartphone, SquareArrowOutUpRight, Timer, TriangleAlert, Zap } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import './style.css';
import './exploration.css';
import { DecisionExplanation } from './decision-explanation';
import { HowItWorks, OfflineNotice, Overview, pages, previewStorageKey, PublicPreview, readPreview, useConnectivity, usePage, targetDescription } from './portal';

const EarthExplorer = lazy(() => import('./earth'));
const ImageLab = lazy(() => import('./image-lab'));
const DataCatalog = lazy(() => import('./data-catalog'));
const Operations = lazy(() => import('./operations'));

const cn = (...values) => twMerge(clsx(values));
const format = (value, digits = 3) => value == null ? '—' : value.toFixed(digits);
const percentage = value => value == null ? 'Unavailable' : value > 0 && value < 0.01 ? '<1%' : value < 1 && value > 0.99 ? '>99%' : `${Math.round(value * 100)}%`;
const sources = { radar: 'Multi-radar', satellite: 'Satellite IR', lightning: 'Lightning', nwp: 'Model context' };
const models = { fusion: 'Learned fusion', advection: 'Motion baseline', persistence: 'Persistence', truth: 'Observed outcome' };

async function api(path, body, signal) {
  let response;
  try {
    response = await fetch(`/api/${path}`, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal } : { signal });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new Error('Cannot reach the VAJRA service. Check your connection and that the local server is running, then retry.');
  }
  if (!response.ok) {
    let detail;
    try { detail = (await response.json()).detail; } catch { detail = 'The service could not complete this request.'; }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return response.json();
}

function download(value, filename) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' }));
  const link = document.createElement('a');
  link.href = url; link.download = filename; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function FieldMap({ run, layer }) {
  const canvas = useRef(null);
  const values = run.layers[layer];
  const grid = run.grid;
  useEffect(() => {
    if (!canvas.current || !values) return;
    const context = canvas.current.getContext('2d');
    const pixels = context.createImageData(grid.width, grid.height);
    for (let y = 0; y < grid.height; y++) for (let x = 0; x < grid.width; x++) {
      const row = grid.row_direction === 'north' ? grid.height - y - 1 : y;
      const value = values[row][x];
      const i = (y * grid.width + x) * 4;
      if (value == null) {
        const shade = (x + y) % 3 === 0 ? 57 : 35;
        pixels.data.set([shade, shade + 9, shade + 16, 255], i);
      } else {
        const p = Math.max(0, Math.min(1, value));
        pixels.data.set([15 + p * 30, 27 + p * 185, 44 + p * 148, 255], i);
      }
    }
    context.putImageData(pixels, 0, 0);
  }, [values, grid]);
  const position = (x, y) => [x / (grid.width - 1) * 100, (grid.row_direction === 'north' ? 1 - y / (grid.height - 1) : y / (grid.height - 1)) * 100];
  const places = run.mode === 'simulation' ? run.sites : [
    { name: 'Lyon', lat: 45.764, lon: 4.8357 }, { name: 'Marseille', lat: 43.2965, lon: 5.3698 }, { name: 'Nice', lat: 43.7102, lon: 7.262 }];
  return <div className="map-container">
    <div className="map-meta"><span>{run.mode === 'simulation' ? 'SIMULATED FIELD' : 'OBSERVED RADAR REPLAY'}</span><span>+{run.horizon} MIN</span></div>
    <div className="map-frame">
      <canvas ref={canvas} width={grid.width} height={grid.height} role="img" aria-label={`${models[layer]} for ${run.target}`} />
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="map-overlay" aria-hidden="true">
        <defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#f8fafc" /></marker></defs>
        {[20, 40, 60, 80].map(n => <g key={n}><line x1={n} y1="0" x2={n} y2="100" /><line x1="0" y1={n} x2="100" y2={n} /></g>)}
        {run.tracks.map(track => {
          const [x, y] = position(track.x, track.y), [ex, ey] = position(track.end_x, track.end_y);
          return <g key={track.id}><circle cx={x} cy={y} r="2.3" fill="none" stroke="#f8fafc" strokeWidth="0.3" /><path d={`M${x},${y} L${ex},${ey}`} stroke="#f8fafc" strokeWidth="0.3" strokeDasharray="1 1" markerEnd="url(#arrow)" /></g>;
        })}
      </svg>
      {places.map(place => {
        const x = (place.lon - grid.west) / (grid.east - grid.west) * 100;
        const y = (grid.north - place.lat) / (grid.north - grid.south) * 100;
        return <span key={place.name} className="place" style={{ left: `${x}%`, top: `${y}%` }}><span className="place-dot" />{place.name.replace(' demo site', '')}</span>;
      })}
      <span className="axis top-left">{grid.north.toFixed(2)}° N</span><span className="axis bottom-left">{grid.south.toFixed(2)}° N</span>
      <span className="axis bottom-right">{grid.east.toFixed(2)}° E</span>
      {run.status === 'unavailable' && layer === 'fusion' && <div className="unavailable-map"><TriangleAlert size={28} /><strong>Forecast unavailable</strong><span>Restore a spatial observation source.</span></div>}
    </div>
    <div className="map-footer"><span>Coordinate grid · {run.mode === 'simulation' ? '4 km cells' : '0.03° sampled grid'}</span><div className="legend"><span>0</span>{[0.1, 0.3, 0.5, 0.7, 0.9].map(p => <i key={p} style={{ background: `rgb(${15 + p * 30}, ${27 + p * 185}, ${44 + p * 148})` }} />)}<span>{run.mode === 'simulation' ? '1 probability' : '1 echo'}</span><span className="missing-key" />Unknown</div></div>
  </div>;
}

function Reliability({ metrics }) {
  const bins = metrics?.reliability.filter(bin => bin.count > 0) ?? [];
  return <svg viewBox="0 0 280 175" role="img" aria-label="Reliability diagram: predicted probability against observed frequency" className="w-full">
    {[0, 0.5, 1].map(n => <g key={n}><line x1="35" x2="260" y1={140 - 110 * n} y2={140 - 110 * n} stroke="#e2e8f0" /><text x="9" y={144 - 110 * n}>{n}</text><text x={32 + 225 * n} y="158">{n}</text></g>)}
    <line x1="35" y1="140" x2="260" y2="30" stroke="#94a3b8" strokeDasharray="4 4" />
    {bins.map(bin => <circle key={bin.bin} cx={35 + 225 * bin.forecast} cy={140 - 110 * bin.observed} r={Math.max(3, Math.min(7, Math.sqrt(bin.count) / 3))} fill="#0d9488"><title>{bin.count} pixels · forecast {percentage(bin.forecast)} · observed {percentage(bin.observed)}</title></circle>)}
    <text x="100" y="173">Forecast probability</text>
  </svg>;
}

function App() {
  const [tab, setTab] = usePage();
  const [menuOpen, setMenuOpen] = useState(false);
  const [preview, setPreview] = useState(readPreview);
  const online = useConnectivity();
  const [request, setRequest] = useState({ mode: 'simulation', seed: 62, step: 8, horizon: 30, hazard: 'lightning', disabled: [], stale: [] });
  const [run, setRun] = useState(null);
  const [layer, setLayer] = useState('fusion');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  const [prep, setPrep] = useState(20);
  const [siteId, setSiteId] = useState('patna');
  const [threshold, setThreshold] = useState(0.5);
  const [minSources, setMinSources] = useState(2);
  const [maxAge, setMaxAge] = useState(10);
  const [savedReceipt, setReceipt] = useState(null);
  const [receiptError, setReceiptError] = useState('');
  const [saving, setSaving] = useState(false);
  const [evaluation, setEvaluation] = useState(null);
  const [saved, setSaved] = useState([]);
  const [panelLoading, setPanelLoading] = useState(false);
  const receipt = !loading && savedReceipt?.run_id === run?.id
    && savedReceipt?.site.id === siteId && savedReceipt.threshold === threshold
    && savedReceipt.preparation_minutes === prep
    && savedReceipt.assessment?.min_recent_spatial_sources === minSources
    && savedReceipt.assessment?.max_source_age_minutes === maxAge ? savedReceipt : null;
  const needsForecast = tab === 'workbench' || tab === 'verification';
  useEffect(() => { setMenuOpen(false); setError(''); }, [tab]);
  useEffect(() => {
    if (!needsForecast) return;
    const controller = new AbortController();
    setLoading(true); setError(''); setReceipt(null);
    api('runs', request, controller.signal).then(result => { setRun(result); setLoading(false); }).catch(e => {
      if (e.name !== 'AbortError') { setError(e.message); setLoading(false); }
    });
    return () => controller.abort();
  }, [request, retry, needsForecast]);
  useEffect(() => {
    const endpoint = tab === 'verification' ? 'evaluation' : tab === 'receipts' ? 'receipts' : null;
    if (!endpoint) return;
    const controller = new AbortController();
    setPanelLoading(true); setError('');
    api(endpoint, undefined, controller.signal).then(result => {
      if (tab === 'verification') setEvaluation(result); else setSaved(result);
      setPanelLoading(false);
    }).catch(e => {
      if (e.name !== 'AbortError') { setError(e.message); setPanelLoading(false); }
    });
    return () => controller.abort();
  }, [tab, retry]);
  const update = patch => setRequest(previous => ({ ...previous, ...patch }));
  const observed = request.mode === 'observed';
  const changeMode = mode => {
    update({ mode, horizon: mode === 'observed' ? 15 : 30, hazard: mode === 'observed' ? 'storm' : 'lightning', disabled: [], stale: [] });
    setLayer(mode === 'observed' ? 'advection' : 'fusion');
  };
  const changeSensor = (source, state) => update({ disabled: [...request.disabled.filter(x => x !== source), ...(state === 'missing' ? [source] : [])], stale: [...request.stale.filter(x => x !== source), ...(state === 'stale' ? [source] : [])] });
  const site = run?.sites.find(site => site.id === siteId);
  const reviewNeeded = site?.probability != null && site.probability >= threshold;
  const windowStart = run ? run.horizon - (run.request.hazard === 'lightning' ? 15 : 0) : 0;
  const deadline = windowStart - prep;
  const currentLayer = run?.layers[layer] ? layer : observed ? 'advection' : 'fusion';
  const activeMetrics = run?.metrics[currentLayer] ?? run?.metrics[observed ? 'advection' : 'fusion'];
  const finiteValues = run?.layers[currentLayer]?.flat().filter(value => value != null) ?? [];
  const peak = finiteValues.length ? Math.max(...finiteValues) : null;
  const nav = [{ id: 'overview', icon: House }, { id: 'earth', icon: Globe2 }, { id: 'workbench', icon: Map }, { id: 'public', icon: Smartphone }, { id: 'flow', icon: BookOpen }, { id: 'operations', icon: Activity }, { id: 'verification', icon: FlaskConical }, { id: 'image-lab', icon: ScanLine }, { id: 'sources', icon: Database }, { id: 'receipts', icon: FileText }];
  function openPreview() {
    try { localStorage.setItem(previewStorageKey, JSON.stringify(receipt)); }
    catch { setReceiptError('Browser storage is unavailable. The sample can be viewed now but will not survive a reload.'); }
    setPreview(receipt); setTab('public');
  }
  function clearPreview() {
    try { localStorage.removeItem(previewStorageKey); }
    catch { return; }
    setPreview(null);
  }
  async function save() {
    setSaving(true); setReceiptError('');
    try { setReceipt(await api('receipts', { run_id: run.id, preparation_minutes: prep, threshold, site_id: siteId, min_recent_spatial_sources: minSources, max_source_age_minutes: maxAge })); }
    catch (e) { setReceiptError(e.message); }
    finally { setSaving(false); }
  }
  return <div className="app-shell">
    <a className="skip-link" href="#main" onClick={e => { e.preventDefault(); document.getElementById('main').focus(); }}>Skip to content</a>
    <aside className="sidebar">
      <div className="brand-row"><a href="#/overview" className="brand"><span className="brand-icon"><Zap size={24} aria-hidden="true" /></span><span>VAJRA<small>Storm intelligence research</small></span></a><button className="mobile-menu" aria-label="Toggle navigation" aria-expanded={menuOpen} aria-controls="main-navigation" onClick={() => setMenuOpen(!menuOpen)}><Menu size={24} aria-hidden="true" /></button></div>
      <div className="side-label">EXPLORE VAJRA</div>
      <nav id="main-navigation" aria-label="Main navigation" className={cn(menuOpen && 'menu-open')}>{nav.map(({ id, icon: Icon }) => <React.Fragment key={id}>{id === 'verification' && <div className="nav-divider">EVIDENCE & RESEARCH</div>}<a href={`#/${id}`} className={cn('nav-item', tab === id && 'nav-active')} aria-current={tab === id ? 'page' : undefined}><Icon size={19} aria-hidden="true" /><span>{pages[id].name}</span>{tab === id && <ChevronRight size={15} aria-hidden="true" />}</a></React.Fragment>)}</nav>
      <div className="sidebar-bottom"><ShieldCheck size={22} /><strong>Evidence before confidence</strong><p>Every result keeps its source, target and model version.</p><span>SIH26072 · Research prototype</span></div>
    </aside>
    <div className="workspace">
      <header className="topbar"><div className="flex items-center gap-2"><span>SIH26072</span><ChevronRight size={14} aria-hidden="true" /><strong>{pages[tab].name}</strong></div><div className="research-tag"><FlaskConical size={16} aria-hidden="true" />Research prototype</div></header>
      {!online && <OfflineNotice />}
      <main id="main" tabIndex="-1">
        <div className="page-heading"><div><p className="eyebrow">OBSERVE · FORECAST · VERIFY</p><h1>{pages[tab].title}</h1><p className="text-slate-600 mt-2">{pages[tab].description}</p></div>{!['overview', 'public', 'flow'].includes(tab) && <a className="button secondary" href="/research/SIH26072_RESEARCH_AND_BLUEPRINT.md" download><FileText size={16} aria-hidden="true" />Research blueprint<ArrowDownToLine size={15} aria-hidden="true" /></a>}</div>
        {tab === 'overview' && <Overview />}
        <Suspense fallback={<div className="lab-loading" role="status">Opening the explorer…</div>}>
          {tab === 'earth' && <EarthExplorer />}
          {tab === 'image-lab' && <ImageLab />}
          {tab === 'sources' && <DataCatalog />}
          {tab === 'operations' && <Operations />}
        </Suspense>
        {tab === 'flow' && <HowItWorks />}
        {tab === 'public' && <PublicPreview preview={preview} onClear={clearPreview} online={online} />}
        {error && <div role="alert" className="error-box">{error}<button className="button secondary" onClick={() => setRetry(n => n + 1)}>Retry request</button></div>}
        {tab === 'workbench' && <>
          <section className="control-bar" aria-label="Forecast controls">
            <label>Data mode<select aria-label="Data mode" value={request.mode} onChange={e => changeMode(e.target.value)}><option value="simulation">Bihar · simulation</option><option value="observed">France · radar replay</option></select></label>
            {!observed && <label>Held-out event<select aria-label="Held-out event" value={request.seed} onChange={e => update({ seed: +e.target.value })}>{[60, 61, 62, 63, 64, 65].map(seed => <option key={seed} value={seed}>Event {seed}</option>)}</select></label>}
            {!observed && <label>Issue time<select aria-label="Issue time" value={request.step} onChange={e => update({ step: +e.target.value })}>{[4, 8, 12, 16].map(value => <option key={value} value={value}>{String(8 + Math.floor(value * 5 / 60)).padStart(2, '0')}:{String(value * 5 % 60).padStart(2, '0')} UTC</option>)}</select></label>}
            <label>Forecast target<select aria-label="Forecast target" value={request.hazard} onChange={e => update({ hazard: e.target.value })} disabled={observed}>{!observed && <option value="lightning">Lightning · 15-min</option>}<option value="storm">{observed ? 'Radar echo ≥20 dBZ' : 'Storm proxy ≥35 dBZ'}</option></select></label>
            <label>Lead time<select aria-label="Lead time" value={request.horizon} onChange={e => update({ horizon: +e.target.value })}>{(observed ? [5, 10, 15, 20] : [15, 30, 60]).map(value => <option key={value} value={value}>+{value} minutes</option>)}</select></label>
          </section>
          <div className={cn('scope-banner', observed && 'observed-banner')}><FlaskConical size={17} /><span><strong>{observed ? 'Observed historical radar.' : 'Synthetic research demonstration.'}</strong> {observed ? 'Météo-France, 19 December 2018. No lightning labels in this sample.' : 'Model probabilities describe generated storms. They are not forecasts for Bihar.'}</span></div>
          <div className="model-strip"><span><strong>Active method</strong>{observed ? 'Global motion extrapolation' : 'Logistic regression · simulator trained'}</span><a href="#/flow">Understand this prediction<ArrowRight size={16} aria-hidden="true" /></a></div>
          {loading && <div role="status" className="loading-state"><RefreshCw size={18} />Computing forecast and verification…</div>}
          {!loading && run && !error && <>
            <div className="stats-row"><div><span>Forecast window</span><strong>+{run.horizon}<small> minutes</small></strong><p>{run.issued_at.replace('T', ' ').replace('+00:00', ' UTC')}</p></div><div><span>Available observation sources</span><strong>{run.sources.filter(s => s.state === 'available').length}<small> / 4</small></strong><p>{run.status === 'degraded' ? 'Source removal experiment' : observed ? 'Historical radar composite' : 'Two overlapping radar instruments'}</p></div><div><span>{currentLayer === 'truth' ? 'Withheld outcome grid points' : observed ? 'Verified grid points' : 'Highest grid-cell probability'}</span><strong>{currentLayer === 'truth' ? finiteValues.length.toLocaleString() : observed ? activeMetrics?.samples.toLocaleString() : percentage(peak)}</strong><p>{currentLayer === 'truth' ? 'Excluded from forecast inputs' : observed ? 'Shared forecast / truth coverage' : 'Not a district-wide probability'}</p></div><div><span>Computation time</span><strong>{run.latency_ms}<small> ms</small></strong><p>Local CPU · recorded first execution</p></div></div>
            <div className="workbench-grid">
              <section className="panel map-panel"><div className="panel-heading"><div><h2>{run.label}</h2><p>{targetDescription(run)}</p></div><Layers size={18} className="text-slate-400" /></div><div className="layer-switch" role="group" aria-label="Map layer">{Object.keys(run.layers).map(key => <button className={cn(currentLayer === key && 'selected')} key={key} onClick={() => setLayer(key)} aria-pressed={currentLayer === key}>{key === 'truth' && run.mode === 'simulation' ? 'Simulated outcome' : models[key]}</button>)}</div><FieldMap run={run} layer={currentLayer} /><div className="map-caption"><span className={cn('status-dot', run.status === 'degraded' || run.status === 'unavailable' ? 'bg-amber-500' : 'bg-teal-600')} /><span>{run.status_reason}</span></div></section>
              <div className="right-column"><section className="panel"><div className="panel-heading"><h2>Observation health</h2><Radio size={18} className="text-slate-400" /></div><p className="panel-intro">{observed ? 'Only radar is included in this open sample.' : 'Test the forecast when observations fail or arrive late.'}</p><div className="source-list">{run.sources.map(source => <div className="source-row" key={source.source}><div><span className={cn('status-dot', source.state === 'available' ? 'bg-teal-600' : 'bg-amber-500')} /><strong>{sources[source.source]}</strong><small>{source.state === 'available' ? observed ? 'Historical observation' : 'Synthetic · current at issue' : source.state === 'stale' ? '45 min old · withheld' : 'No observation'}</small></div><label className="sr-only" htmlFor={`source-${source.source}`}>{sources[source.source]} availability</label><select id={`source-${source.source}`} value={source.state} disabled={observed} onChange={e => changeSensor(source.source, e.target.value)}><option value="available">Available</option><option value="missing">Missing</option><option value="stale">Stale</option></select></div>)}</div></section>
              <details className="panel evidence-panel"><summary>Evidence at issue time<Activity size={18} aria-hidden="true" /></summary><dl className="evidence-list">{run.evidence.map(item => <div key={item.name}><dt>{item.name}</dt><dd>{item.value}</dd></div>)}</dl><p className="panel-footnote">Input cues describe observations. They are not causal explanations of the model.</p></details></div>
            </div>
            <div className="bottom-grid"><section className="panel"><div className="panel-heading"><div><h2>Does the model beat the baseline?</h2><p>This replay only · common valid coverage · threshold 0.5</p></div><FlaskConical size={18} className="text-slate-400" /></div><div className="table-scroll"><table><thead><tr><th>Method</th><th>CSI ↑</th><th>POD ↑</th><th>FAR ↓</th><th>Brier ↓</th></tr></thead><tbody>{Object.entries(run.metrics).map(([name, metric]) => <tr key={name}><td>{models[name]}</td><td>{format(metric.csi)}</td><td>{format(metric.pod)}</td><td>{format(metric.far)}</td><td>{format(metric.brier)}</td></tr>)}</tbody></table></div><p className="panel-footnote">A baseline may win. Undefined scores are shown as —. {observed ? 'Binary echo forecasts are not calibrated probabilities.' : 'Synthetic scores cannot establish Indian forecasting skill.'}</p><button className="text-button" onClick={() => setTab('verification')}>Open verification lab<ArrowRight size={15} /></button></section>
              <section className="panel decision-panel"><div className="panel-heading"><h2>Time to act</h2><Timer size={18} className="text-slate-400" /></div>{observed ? <div className="empty-state"><ShieldCheck size={26} /><strong>No lightning decision from this sample</strong><p>A radar echo alone cannot supply a verified lightning probability.</p><button className="button secondary" onClick={() => changeMode('simulation')}>Open simulation</button></div> : <><div className="decision-controls"><label>Demo location<select aria-label="Demo location" value={siteId} onChange={e => { setSiteId(e.target.value); setReceipt(null); }}>{run.sites.map(site => <option key={site.id} value={site.id}>{site.name}</option>)}</select></label><label>Preparation time<select aria-label="Preparation time" value={prep} onChange={e => { setPrep(+e.target.value); setReceipt(null); }}>{[5, 10, 15, 20, 30, 45].map(value => <option key={value} value={value}>{value} minutes</option>)}</select></label></div><div className="threshold-row"><label htmlFor="threshold">Demo review threshold</label><select id="threshold" value={threshold} onChange={e => { setThreshold(+e.target.value); setReceipt(null); }}>{[0.1, 0.3, 0.5, 0.7, 0.9].map(value => <option key={value} value={value}>{percentage(value)}</option>)}</select></div><div className="decision-controls"><label>Required recent sources<select aria-label="Required recent sources" value={minSources} onChange={e => { setMinSources(+e.target.value); setReceipt(null); }}>{[1, 2, 3].map(value => <option key={value} value={value}>{value} spatial source types</option>)}</select></label><label>Maximum source age<select aria-label="Maximum source age" value={maxAge} onChange={e => { setMaxAge(+e.target.value); setReceipt(null); }}>{[0, 5, 10, 15, 30].map(value => <option key={value} value={value}>{value} minutes</option>)}</select></label></div><p className="panel-footnote">Probability preview below. Saving applies the observation checks and records the reasons.</p><div className="decision-result"><div><span>Local model probability</span><strong>{percentage(site?.probability)}</strong></div><p>{site?.probability == null ? 'Insufficient observations. No all-clear can be inferred.' : reviewNeeded ? deadline <= 0 ? `Review now. The illustrative deadline is ${Math.abs(deadline)} min before issue time.` : `Illustrative decision deadline: ${deadline} min after issue time.` : 'Below the selected demo threshold. This is not an all-clear.'}</p></div><p className="panel-footnote">Forecast window start minus preparation time. No exact strike ETA. No shelter suitability has been verified.</p><button className="button primary w-full" disabled={saving || loading} onClick={save}><FileText size={16} />{saving ? 'Saving…' : 'Save decision receipt'}</button>{receiptError && <p role="alert" className="text-red-700 text-sm mt-2">{receiptError}</p>}{receipt && <div role="status" className="saved-receipt"><Check size={16} />Saved locally<button onClick={() => download(receipt, `vajra-receipt-${receipt.id}.json`)}>Export JSON<ArrowDownToLine size={13} /></button></div>}</>}</section></div>
            {receipt?.assessment && <DecisionExplanation assessment={receipt.assessment} />}
          <div className="run-footer"><span>Run {run.id} · {run.model_version}</span><button className="text-button" onClick={() => download(run, `vajra-run-${run.id}.json`)}><ArrowDownToLine size={14} />Export forecast & evidence</button></div>
            {receipt && <div className="preview-action"><div><strong>See how this sample reads on a phone.</strong><p>Save a labelled simulation brief to this browser for offline viewing.</p></div><button className="button secondary" onClick={openPreview}><Smartphone size={18} aria-hidden="true" />View public preview</button></div>}
          </>}
        </>}
        {tab === 'verification' && <><div className="scope-banner"><FlaskConical size={18} /><span>Software verification and scientific forecast validation answer different questions. These results do not establish operational Indian skill.</span></div><div className="bottom-grid"><section className="panel"><div className="panel-heading"><h2>Current replay reliability</h2><span className="small-tag">{run?.mode ?? 'Waiting'}</span></div><Reliability metrics={run?.metrics.fusion ?? run?.metrics.advection} /><p className="panel-footnote">Observed frequency on the vertical axis; predicted probability on the horizontal axis. Each dot is a populated probability bin. One case is too small to establish calibration.</p></section><section className="panel"><div className="panel-heading"><h2>Evaluation contract</h2><ShieldCheck size={18} /></div><dl className="evidence-list"><div><dt>Train / validation / test</dt><dd>24 / 6 / 6 disjoint synthetic events</dd></div><div><dt>Forecast lead times</dt><dd>15, 30 and 60 minutes</dd></div><div><dt>Lightning label</dt><dd>Any simulated flash within 8 km during the 15-minute window ending at lead time</dd></div><div><dt>Calibration</dt><dd>Temperature chosen on validation events only</dd></div><div><dt>Observed radar example</dt><dd>France; +5 to +20 minutes; echo ≥20 dBZ</dd></div></dl></section></div><section className="panel mt-6"><div className="panel-heading"><div><h2>Held-out simulator results</h2><p>Complete-source runs, all six test events. Missing-source experiments are included in the exported report.</p></div>{evaluation && <button className="button secondary" onClick={() => download(evaluation, 'vajra-evaluation.json')}><ArrowDownToLine size={15} />Export report</button>}</div><div className="table-scroll"><table><thead><tr><th>Target</th><th>Lead</th><th>Model</th><th>CSI ↑</th><th>POD ↑</th><th>FAR ↓</th><th>Brier ↓</th><th>Pixels</th></tr></thead><tbody>{evaluation?.scores.filter(score => score.disabled.length === 0).map(score => <tr key={`${score.hazard}-${score.horizon}-${score.model}`}><td>{score.hazard === 'storm' ? 'Convective proxy' : 'Lightning'}</td><td>+{score.horizon}m</td><td>{models[score.model]}</td><td>{format(score.csi)}</td><td>{format(score.pod)}</td><td>{format(score.far)}</td><td>{format(score.brier)}</td><td>{score.samples.toLocaleString()}</td></tr>)}</tbody></table></div>{!evaluation && <p className="panel-intro">Loading the recorded experiment…</p>}</section></>}
        {tab === 'sources' && <><div className="research-grid">{[{ title: 'Problem & evidence', path: 'PROBLEM_EVIDENCE.md', text: 'Official statement, verified impact figures, existing services, survey evidence and unresolved claims.', icon: FileText }, { title: 'Training data atlas', path: 'DATA_SOURCES.md', text: 'Indian and global datasets, access steps, licences, sampling, targets and transfer limitations.', icon: Database }, { title: 'Model & evaluation', path: 'MODEL_RESEARCH.md', text: 'Primary literature, causal alignment, calibration, event splits and the next spatial model.', icon: FlaskConical }].map(item => <a key={item.path} className="panel research-card" href={`/research/${item.path}`} download><item.icon size={27} /><h2>{item.title}</h2><p>{item.text}</p><span>Read research<ArrowDownToLine size={16} /></span></a>)}</div><section className="panel mt-6"><div className="panel-heading"><h2>What is established, and what is still a hypothesis</h2></div><div className="research-prose"><p>IMD, Damini, SACHET and NOAA already provide substantial forecasting, sensor fusion and alerting capabilities. Multisensor maps and multilingual notifications alone do not establish novelty.</p><p>VAJRA tests a narrower proposition: an operator can inspect the evidence, see a forecast fail or degrade, compare its skill, and preserve the basis of a local decision. Better Indian nowcasting remains a research hypothesis until paired Indian observations and held-out outcomes are available.</p><p>The bundled MétéoNet files are actual historical observations with verified checksums and an Etalab Open Licence. Simulator model weights are trained locally. No live Indian radar, satellite or lightning forecast feed is connected.</p><div className="external-links"><a href="https://www.sih.gov.in/sih2026PS" target="_blank" rel="noreferrer">Official SIH statement<SquareArrowOutUpRight size={14} /></a><a href="https://meteofrance.github.io/meteonet/english/data/rain-radar/" target="_blank" rel="noreferrer">MétéoNet documentation<SquareArrowOutUpRight size={14} /></a></div></div></section></>}
        {tab === 'receipts' && <section className="panel"><div className="panel-heading"><h2>Saved review records</h2><span className="small-tag">{saved.length} local records</span></div>{panelLoading ? <div className="empty-state" role="status">Loading saved records…</div> : error ? <div className="empty-state">Records could not be loaded. Use Retry request above.</div> : saved.length === 0 ? <div className="empty-state"><FileText size={30} /><strong>No decision receipts yet</strong><p>Review a synthetic forecast and save its evidence.</p><button className="button primary" onClick={() => setTab('workbench')}>Open workbench</button></div> : <div className="table-scroll"><table><thead><tr><th>Receipt</th><th>Location</th><th>Probability</th><th>Outcome</th><th>Record</th></tr></thead><tbody>{saved.map(item => <tr key={item.id}><td className="font-mono">{item.id.slice(0, 10)}</td><td>{item.site.name}</td><td>{percentage(item.site.probability)}</td><td>{item.status.replaceAll('_', ' ')}</td><td><button className="text-button" onClick={() => download(item, `vajra-receipt-${item.id}.json`)}>Export<ArrowDownToLine size={13} /></button></td></tr>)}</tbody></table></div>}</section>}
        {tab === 'sources' && <div className="research-grid section-block">{[{ title: 'Product & algorithm flow', path: 'PRODUCT_FLOW_AND_ALGORITHMS.md', text: 'A simple explanation of the working model, recommended architecture, users, website and app.' }, { title: 'Review of the friend notes', path: 'FRIEND_NOTES_REVIEW.md', text: 'What to keep, what to test, and which claims the primary research does not support.' }, { title: 'Jev: where it fits', path: 'JEV_ASSESSMENT.md', text: 'Hosted execution, optional review routing, documented limitations and offline alternatives.' }].map(item => <a key={item.path} className="panel research-card" href={`/research/${item.path}`} download><FileText size={27} aria-hidden="true" /><h2>{item.title}</h2><p>{item.text}</p><span>Read assessment<ArrowDownToLine size={16} aria-hidden="true" /></span></a>)}</div>}
        <footer className="page-footer"><span>VAJRA / SIH26072</span><span>Research prototype · Consult official IMD / NDMA warnings for real decisions.</span></footer>
      </main>
    </div>
  </div>;
}

createRoot(document.getElementById('root')).render(<React.StrictMode><App /></React.StrictMode>);

if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(error => console.warn('Offline app shell could not be installed:', error.message));
  });
}
