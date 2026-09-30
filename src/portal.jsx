import React, { useEffect, useState } from 'react';
import { ArrowDownToLine, ArrowRight, BookOpen, Check, CloudLightning, Database, FileText, FlaskConical, Layers, MapPin, Radio, ShieldCheck, Smartphone, Timer, WifiOff, Zap } from 'lucide-react';

export const pages = {
  overview: { name: 'Overview', title: 'Understand the storm. Prepare with evidence.', description: 'A research prototype for short-term thunderstorm and lightning forecasts.' },
  earth: { name: 'Earth explorer', title: 'A planet of perspective.', description: 'Find a place. Explore the observations. Follow the evidence.' },
  'image-lab': { name: 'Image processing lab', title: 'Every image has a story.', description: 'Prepare observed radar, estimate its motion, and measure what changed.' },
  workbench: { name: 'Officer workbench', title: 'Nowcast workbench', description: 'Replay an event, inspect the evidence, and record a review.' },
  public: { name: 'Public preview', title: 'Weather information, made clear.', description: 'Explore the mobile experience we are designing for communities.' },
  flow: { name: 'How it works', title: 'From observations to a decision.', description: 'Follow the working pipeline and see what we need to build next.' },
  verification: { name: 'Verification lab', title: 'Put the forecast to the test', description: 'Computed baselines and held-out outcomes. Every score has a defined scope.' },
  sources: { name: 'Research & data', title: 'Built on traceable evidence', description: 'The problem, prior art, data access, and a practical route to Indian validation.' },
  receipts: { name: 'Decision receipts', title: 'A record of each decision', description: 'Local simulation records. No warnings are transmitted.' },
};

export function usePage() {
  const read = () => {
    const key = window.location.hash.replace('#/', '');
    return Object.hasOwn(pages, key) ? key : 'overview';
  };
  const [page, updatePage] = useState(read);
  useEffect(() => {
    const onHashChange = () => {
      updatePage(read());
      document.getElementById('main')?.focus({ preventScroll: true });
      window.scrollTo(0, 0);
    };
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);
  useEffect(() => { document.title = `${pages[page].name} | VAJRA`; }, [page]);
  return [page, next => { window.location.hash = `/${next}`; }];
}

export function useConnectivity() {
  const [online, setOnline] = useState(navigator.onLine);
  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    window.addEventListener('online', update);
    window.addEventListener('offline', update);
    return () => { window.removeEventListener('online', update); window.removeEventListener('offline', update); };
  }, []);
  return online;
}

export function Overview() {
  return <>
    <section className="intro-grid">
      <div className="intro-copy">
        <span className="status-pill"><FlaskConical size={16} aria-hidden="true" /> Working research prototype</span>
        <h2>A storm can change before the next forecast arrives.</h2>
        <p>Our goal is to help a local officer understand where a storm may develop, how reliable the evidence is, and how much time people need to prepare.</p>
        <a className="button primary" href="#/workbench">Explore the officer workbench<ArrowRight size={18} aria-hidden="true" /></a>
        <a className="intro-link" href="#/flow">See how the predictions work<ArrowRight size={16} aria-hidden="true" /></a>
      </div>
      <div className="system-preview" aria-label="Four sources feed a forecast, followed by officer review and community information">
        <div className="preview-label"><span>THE PROPOSED WORKFLOW</span><Layers size={18} aria-hidden="true" /></div>
        <div className="sensor-tiles">{[[Radio, 'Radar', 'Storm structure'], [CloudLightning, 'Satellite', 'Cloud growth'], [Zap, 'Lightning', 'Recent activity'], [Database, 'Weather model', 'Atmospheric context']].map(([Icon, name, text]) => <div key={name}><Icon size={21} aria-hidden="true" /><strong>{name}</strong><span>{text}</span></div>)}</div>
        <div className="preview-connector" aria-hidden="true" />
        <div className="forecast-node"><CloudLightning size={27} aria-hidden="true" /><div><strong>One shared forecast engine</strong><span>What may happen · where · when</span></div></div>
        <div className="preview-connector" aria-hidden="true" />
        <div className="delivery-nodes"><span><ShieldCheck size={19} aria-hidden="true" />Officer reviews evidence</span><span><Smartphone size={19} aria-hidden="true" />Community receives a brief</span></div>
        <p>Today: simulated fusion + historical radar replay.<br />Live Indian observations and public alerts are future work.</p>
      </div>
    </section>
    <div className="explorer-promo"><div><h3>Begin with a place on Earth.</h3><p>An interactive globe, traceable coordinates and a closer look at the observations.</p></div><a className="button" href="#/earth">Open Earth explorer<ArrowRight size={18} aria-hidden="true" /></a></div>
    <section className="section-block" aria-labelledby="audiences-heading">
      <div className="section-heading"><div><p className="eyebrow">ONE ENGINE, DIFFERENT NEEDS</p><h2 id="audiences-heading">Built for officers. Designed to reach people.</h2></div></div>
      <div className="audience-grid">
        <a href="#/workbench" className="audience-card"><ShieldCheck size={25} aria-hidden="true" /><h3>Officers & forecasters</h3><p>Examine the map, test missing observations, compare predictions with outcomes, and save the evidence behind a decision.</p><span>Open workbench<ArrowRight size={18} aria-hidden="true" /></span></a>
        <a href="#/public" className="audience-card"><Smartphone size={25} aria-hidden="true" /><h3>People & local teams</h3><p>See a simpler sample brief for a selected place. The mobile layout keeps the location, time and information status together.</p><span>Explore public preview<ArrowRight size={18} aria-hidden="true" /></span></a>
      </div>
    </section>
    <section className="section-block panel readiness-panel"><div><p className="eyebrow">WHAT YOU CAN TRY TODAY</p><h2>A complete experiment you can inspect.</h2><p>Run a forecast, remove a source, compare the result, then save its decision receipt. The real radar replay uses an open French dataset.</p></div><ul><li><Check size={18} aria-hidden="true" />Trained simulator model</li><li><Check size={18} aria-hidden="true" />Real historical radar sample</li><li><Check size={18} aria-hidden="true" />Local evidence & exports</li><li><Timer size={18} aria-hidden="true" />Indian forecast validation still needed</li></ul></section>
  </>;
}

const pipeline = [
  { icon: Database, name: 'Read the observations', simple: 'Bring together recent measurements of the same place.', now: 'Generated radar, cloud, lightning and model fields. A separate real radar replay.', next: 'Connect authorised Indian feeds and retain the time each file actually arrived.' },
  { icon: Radio, name: 'Check what we can trust', simple: 'Late or missing data must stay visibly missing.', now: 'Source masks, simulated stale-source removal and radar blending in linear reflectivity.', next: 'Per-pixel quality, sensor age, beam blockage and coverage-aware labels.' },
  { icon: CloudLightning, name: 'Estimate what happens next', simple: 'Learn from recent conditions and compare with moving the current storm forward.', now: 'Six logistic probability models on simulated data. Global motion extrapolation for the real radar sample.', next: 'Motion plus learned growth, persistent storm histories and a first-lightning model.' },
  { icon: FlaskConical, name: 'Measure the mistakes', simple: 'Compare each forecast with observations that were hidden when it ran.', now: 'Held-out synthetic events, common-coverage scores and a reliability diagram.', next: 'Independent Indian storms, seasons and locations, including initiation and sensor outages.' },
  { icon: ShieldCheck, name: 'Review, then communicate', simple: 'Give an officer the evidence and the public a clear, approved message.', now: 'Local simulation decision receipts and a public layout preview.', next: 'Authenticated review, approved warning feeds, expiry, updates and delivery receipts.' },
];

export function HowItWorks() {
  return <>
    <div className="explain-note"><BookOpen size={23} aria-hidden="true" /><p><strong>Think of VAJRA as a storm watch desk.</strong> Sensors tell us what is happening. The forecast estimates what may happen next. An officer reviews the evidence before any real public warning would be issued.</p></div>
    <ol className="pipeline">{pipeline.map((stage, index) => <li key={stage.name}><span className="stage-number">{index + 1}</span><div className="stage-content"><div className="stage-heading"><stage.icon size={22} aria-hidden="true" /><h2>{stage.name}</h2></div><p>{stage.simple}</p><div className="stage-comparison"><div><span className="stage-label">Working today</span><p>{stage.now}</p></div><div><span className="stage-label future-label">Next research step</span><p>{stage.next}</p></div></div></div></li>)}</ol>
    <section className="panel section-block"><div className="panel-heading"><h2>Which prediction am I looking at?</h2></div><div className="table-scroll"><table><thead><tr><th>Mode</th><th>Method</th><th>Meaning of the result</th></tr></thead><tbody><tr><td>Simulated lightning</td><td>Logistic regression + temperature scaling</td><td>A simulated flash within 8 km in one 15-minute window</td></tr><tr><td>Simulated storm</td><td>Separate logistic regression heads</td><td>Reflectivity ≥35 dBZ at the selected lead time</td></tr><tr><td>Real French radar</td><td>Global motion + image translation</td><td>Radar echo ≥20 dBZ at +5 to +20 minutes</td></tr></tbody></table></div><p className="panel-footnote">The +30-minute lightning output covers minutes 15–30. The +60-minute output covers minutes 45–60. These are different windows, so the second probability can be lower.</p></section>
    <div className="audience-grid section-block"><section className="panel prose-card"><h2>What would make this distinctive?</h2><p>Test whether tracking storm development and knowing which sensors to trust improves warning lead time when observations are incomplete.</p><p>We need measurements before claiming better accuracy. Storm lineage, a first-lightning head and selective high-resolution processing are proposed experiments.</p></section><section className="panel prose-card"><h2>Where does Jev fit?</h2><p>Jev could help route a written operator note to the right reviewer. Forecast probabilities and timestamp rules stay in the weather model and ordinary code.</p><p>The documented Jev service runs online. It is optional and is not connected to this prototype.</p></section></div>
    <a className="button secondary" href="/research/PRODUCT_FLOW_AND_ALGORITHMS.md" download><ArrowDownToLine size={18} aria-hidden="true" />Download the detailed plan</a>
  </>;
}

export const previewStorageKey = 'vajra-simulation-preview-v1';
export function targetDescription(record) {
  const horizon = record.horizon ?? record.request?.horizon;
  if (record.request?.hazard === 'lightning' && horizon != null) {
    return `Simulated lightning within 8 km · minutes ${horizon - 15}–${horizon} after issue`;
  }
  return record.target;
}
export function readPreview() {
  try {
    const value = JSON.parse(localStorage.getItem(previewStorageKey));
    return value?.type === 'Simulation decision receipt' && typeof value.site?.name === 'string' && typeof value.issued_at === 'string' && typeof value.target === 'string' ? value : null;
  } catch { return null; }
}

function InstallApp() {
  const [prompt, setPrompt] = useState(null);
  const [installed, setInstalled] = useState(window.matchMedia('(display-mode: standalone)').matches);
  useEffect(() => {
    const available = event => { event.preventDefault(); setPrompt(event); };
    const complete = () => { setPrompt(null); setInstalled(true); };
    window.addEventListener('beforeinstallprompt', available);
    window.addEventListener('appinstalled', complete);
    return () => { window.removeEventListener('beforeinstallprompt', available); window.removeEventListener('appinstalled', complete); };
  }, []);
  async function install() {
    await prompt.prompt();
    await prompt.userChoice;
    setPrompt(null);
  }
  return <section className="panel prose-card"><Smartphone size={26} aria-hidden="true" /><h2>One website. A mobile app experience.</h2><p>This web app can be added to your home screen in supported browsers. The introduction, guide and saved sample brief remain readable after an offline reload.</p>{prompt ? <button className="button primary" onClick={install}>Install VAJRA<ArrowDownToLine size={17} aria-hidden="true" /></button> : <p className="install-hint">{installed ? 'VAJRA is open in app mode.' : 'Use your browser’s Install app or Add to Home Screen option when available. Phone installation requires an HTTPS deployment.'}</p>}<p>New forecasts require access to the backend. A saved sample cannot tell you whether it is safe outside.</p></section>;
}

export function PublicPreview({ preview, onClear, online }) {
  const [place, setPlace] = useState('Patna');
  return <>
    <div className="scope-banner"><FlaskConical size={19} aria-hidden="true" /><span><strong>Design preview only.</strong> No official warning feed is connected. Every brief shown here is a sample.</span></div>
    <div className="public-grid"><section className="public-brief panel" aria-labelledby="brief-heading">
      <div className="brief-top"><span className="status-pill"><FileText size={15} aria-hidden="true" />{preview ? 'Saved simulation' : 'Example layout'}</span><span>{online ? 'Preview' : 'Stored on this device'}</span></div>
      <div className="brief-location"><MapPin size={23} aria-hidden="true" /><div><span>Selected place</span><h2 id="brief-heading">{preview ? preview.site.name.replace(' demo site', '') : place}</h2></div></div>
      {!preview && <label className="location-select">Explore a sample location<select value={place} onChange={e => setPlace(e.target.value)}><option>Patna</option><option>Gaya</option><option>Nalanda</option></select></label>}
      <div className="brief-status"><CloudLightning size={34} aria-hidden="true" /><h3>{preview ? 'Historical sample. Not a current warning.' : 'Live weather information is unavailable.'}</h3><p>{preview ? 'This brief was created from an officer’s saved simulation. It cannot describe current conditions at this location.' : 'This prototype does not receive official local warnings. An empty screen or a low model value must never be treated as an all-clear.'}</p></div>
      {preview && <dl className="brief-facts"><div><dt>Sample issue time</dt><dd>{preview.issued_at.replace('T', ' ').replace('+00:00', ' UTC')}</dd></div><div><dt>What the sample estimates</dt><dd>{targetDescription(preview)}</dd></div><div><dt>Public delivery</dt><dd>Preview on this device only</dd></div></dl>}
      <a className="button primary" href="https://sachet.ndma.gov.in/" target="_blank" rel="noreferrer">Check official SACHET warnings<ArrowRight size={17} aria-hidden="true" /></a>
      <p className="external-note">The official website needs an internet connection.</p>
      {preview && <button className="text-button" onClick={onClear}>Remove this saved sample</button>}
    </section><div className="public-side"><InstallApp /><section className="panel prose-card"><ShieldCheck size={26} aria-hidden="true" /><h2>How a real brief would reach you</h2><ol className="plain-steps"><li>An authorised officer reviews the forecast.</li><li>An approved bulletin names the area, validity period and action.</li><li>Your app shows the latest bulletin and clearly marks expired information.</li></ol><p>That publication workflow still needs to be built and connected to an authorised service.</p></section></div></div>
  </>;
}

export function OfflineNotice() {
  return <div className="offline-notice" role="status"><WifiOff size={19} aria-hidden="true" /><span><strong>Your device is offline.</strong> You can read the guide and a saved sample. Fresh observations and official warning updates are unavailable.</span></div>;
}
