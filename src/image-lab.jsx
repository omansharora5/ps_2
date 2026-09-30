import React, { useEffect, useRef, useState } from 'react';
import { ArrowDownToLine, ArrowRight, Check, FlaskConical, Layers, RefreshCw, ScanLine } from 'lucide-react';
import { downloadJSON, serviceJSON } from './service-client';
import './exploration.css';

const numeric = value => typeof value === 'number' && Number.isFinite(value) ? value.toFixed(3) : '—';
const stops = [[0, [12, 25, 43]], [10, [24, 68, 85]], [20, [34, 134, 133]], [35, [121, 218, 183]], [50, [247, 203, 105]], [65, [249, 112, 84]]];
function radarColor(value) {
  for (let i = 1; i < stops.length; i++) {
    if (value <= stops[i][0]) {
      const t = Math.max(0, (value - stops[i - 1][0]) / (stops[i][0] - stops[i - 1][0]));
      return stops[i][1].map((v, c) => Math.round(stops[i - 1][1][c] * (1 - t) + v * t));
    }
  }
  return stops.at(-1)[1];
}

function RadarImage({ values, grid, name, description, segment = false }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!values || !ref.current) return;
    const context = ref.current.getContext('2d');
    const image = context.createImageData(grid.width, grid.height);
    for (let y = 0; y < grid.height; y++) for (let x = 0; x < grid.width; x++) {
      const row = grid.row_direction === 'north' ? grid.height - 1 - y : y;
      const value = values[row][x];
      const i = (y * grid.width + x) * 4;
      const color = value == null ? ((x + y) % 4 < 2 ? [75, 83, 101] : [42, 49, 64]) : segment ? (value === 0 ? [12, 25, 43] : [70 + value * 41 % 170, 115 + value * 53 % 130, 85 + value * 67 % 160]) : radarColor(value);
      image.data.set([...color, 255], i);
    }
    context.putImageData(image, 0, 0);
  }, [values, grid, segment]);
  return <figure className="radar-figure"><figcaption><strong>{name}</strong><span>{description}</span></figcaption><div className="radar-image"><canvas ref={ref} width={grid.width} height={grid.height} role="img" aria-label={name} /><span className="map-north">N ↑</span><span className="map-unit">{segment ? 'OBJECT IDs' : 'REFLECTIVITY / dBZ'}</span></div></figure>;
}

export default function ImageLab() {
  const [catalog, setCatalog] = useState(null);
  const [parameters, setParameters] = useState({ method: 'global_translation', preprocessing: 'smooth', horizon: 10 });
  const [run, setRun] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(true);
  const [retry, setRetry] = useState(0);
  const [objects, setObjects] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    setBusy(true); setError(''); setRun(null);
    Promise.all([
      serviceJSON('image-methods', { signal: controller.signal }),
      serviceJSON('image-runs', { body: parameters, signal: controller.signal }),
    ]).then(([methods, result]) => { setCatalog(methods); setRun(result); setBusy(false); }).catch(error => {
      if (error.name !== 'AbortError') { setError(error.message); setBusy(false); }
    });
    return () => controller.abort();
  }, [parameters, retry]);
  const methodLabel = catalog?.methods.find(method => method.id === parameters.method)?.label;
  return <div className="image-lab">
    <div className="lab-intro"><span className="lab-icon"><ScanLine size={27} aria-hidden="true" /></span><div><p className="eyebrow">REAL INPUTS. VISIBLE TRANSFORMATIONS.</p><h2>Follow an echo from image to estimate.</h2><p>Clean a measured radar image, choose a motion method, and compare it with the later observation.</p></div><a className="button secondary" href="#/sources">Data & provenance<ArrowRight size={16} aria-hidden="true" /></a></div>
    <div className="scope-banner observed-banner"><Check size={19} aria-hidden="true" /><span><strong>Historical French radar.</strong> These are measured MétéoNet images. This experiment forecasts radar echoes, not lightning or present weather.</span></div>
    <section className="control-bar lab-controls" aria-label="Image experiment controls">
      <label>Motion method<select aria-label="Motion method" value={parameters.method} onChange={event => setParameters({ ...parameters, method: event.target.value })}>{(catalog?.methods || [{ id: 'global_translation', label: 'Global image translation' }]).map(method => <option key={method.id} value={method.id}>{method.label}</option>)}</select></label>
      <label>Image preparation<select aria-label="Image preparation" value={parameters.preprocessing} onChange={event => setParameters({ ...parameters, preprocessing: event.target.value })}>{(catalog?.preprocessing || [{ id: 'smooth', label: 'Masked smoothing' }]).map(method => <option key={method.id} value={method.id}>{method.label}</option>)}</select></label>
      <label>Forecast lead<select aria-label="Image forecast lead" value={parameters.horizon} onChange={event => setParameters({ ...parameters, horizon: Number(event.target.value) })}>{(catalog?.horizons || [5, 10, 15, 20]).map(value => <option key={value} value={value}>{value} minutes</option>)}</select></label>
      <button className="button primary" onClick={() => setRetry(value => value + 1)} disabled={busy}><RefreshCw size={16} aria-hidden="true" />{busy ? 'Processing…' : 'Re-run experiment'}</button>
    </section>
    {error && <div className="error-box" role="alert"><span>{error}</span><button className="button secondary" onClick={() => setRetry(value => value + 1)}>Retry image experiment</button></div>}
    {busy && <div className="lab-loading" role="status"><ScanLine size={30} aria-hidden="true" /><h3>Processing the observed radar</h3><p>Preserving missing pixels and keeping the future outcome separate.</p></div>}
    {run && <div data-testid="image-result" data-run-id={run.id}>
      <div className="experiment-description"><p>{catalog?.methods.find(method => method.id === run.method)?.description}</p><span>{run.horizon} MINUTE LEAD</span></div>
      <div className="radar-grid"><RadarImage values={run.layers.original} grid={run.grid} name="01 / Original observation" description="The measured image at issue time" /><RadarImage values={run.layers.processed} grid={run.grid} name="02 / Prepared image" description={catalog?.preprocessing.find(method => method.id === run.preprocessing)?.label || run.preprocessing} /><RadarImage values={objects ? run.layers.segments : run.layers.forecast} grid={run.grid} name={objects ? '03 / Observed echo objects' : '03 / Forecast image'} description={objects ? 'Connected regions in the prepared observation' : `${methodLabel} · +${run.horizon} min`} segment={objects} /><RadarImage values={run.layers.truth} grid={run.grid} name="04 / Later observed outcome" description="Held out from image processing and motion estimation" /></div>
      <div className="radar-legend"><span>0</span><i aria-hidden="true" /><span>65 dBZ</span><span className="lab-missing-key">▨ Missing observation</span><button className="button secondary" aria-pressed={objects} onClick={() => setObjects(!objects)}><Layers size={16} aria-hidden="true" />{objects ? 'Show forecast' : 'Show echo objects'}</button></div>
      <div className="lab-bottom-grid"><section className="panel"><div className="panel-heading"><div><h2>Compare on the same valid pixels</h2><p>Lower image error is better. Higher CSI / FSS is better.</p></div><FlaskConical size={20} aria-hidden="true" /></div><div className="table-scroll"><table><thead><tr><th>Method</th><th>MAE dBZ</th><th>RMSE dBZ</th><th>CSI</th><th>FSS</th></tr></thead><tbody>{[['selected', 'Selected method'], ['persistence', 'Raw persistence']].map(([key, label]) => <tr key={key}><td>{label}</td><td>{numeric(run.metrics[key]?.mae_dbz)}</td><td>{numeric(run.metrics[key]?.rmse_dbz)}</td><td>{numeric(run.metrics[key]?.csi)}</td><td>{numeric(run.metrics[key]?.fss)}</td></tr>)}</tbody></table></div><p className="panel-footnote">{run.metrics.selected?.samples ?? '—'} common valid pixels for echo scores; {run.metrics.selected?.intensity_samples ?? 'unavailable'} observed-echo pairs for dBZ errors. {run.metrics.selected?.intensity_note}. Scores describe this replay only. Undefined values appear as —.</p></section><section className="panel lab-evidence"><h2>Keep the evidence attached</h2><dl><div><dt>Issue time</dt><dd>{run.issued_at}</dd></div><div><dt>Outcome time</dt><dd>{run.valid_at}</dd></div><div><dt>Echo objects</dt><dd>{run.segmentation.objects.length} at ≥{run.segmentation.threshold_dbz} dBZ</dd></div></dl><p>{run.time_note}</p><button className="button secondary" onClick={() => downloadJSON(run, `vajra-image-${run.id}.json`)}><ArrowDownToLine size={16} aria-hidden="true" />Export images, metrics & provenance</button></section></div>
      <details className="panel lab-provenance"><summary>Processing details and source provenance</summary><p>{run.scope}</p><p>{run.target}</p><ul>{run.limitations.map(item => <li key={item}>{item}</li>)}</ul><h3>Processing</h3><pre>{JSON.stringify(run.processing, null, 2)}</pre><h3>Provenance</h3><pre>{JSON.stringify(run.provenance, null, 2)}</pre></details>
    </div>}
  </div>;
}
