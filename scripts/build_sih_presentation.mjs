import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';

// The source deck is user-owned and deliberately not redistributed in this repo.
const source = process.argv[2] || 'C:/Users/dell/Downloads/VMD-slide2-flow-updated.pptx';
const buildDir = path.resolve('.presentation-build');
const runtime = process.env.CODEX_PRESENTATION_RUNTIME || 'C:/Users/dell/.cache/codex-runtimes/codex-primary-runtime/dependencies/node';
const requireRuntime = createRequire(path.join(runtime, 'package.json'));
const { FileBlob, PresentationFile } = await import(pathToFileURL(requireRuntime.resolve('@oai/artifact-tool')));
const p = await PresentationFile.importPptx(await FileBlob.load(source));
console.log('Imported reference');
if (p.slides.items.length !== 6) throw new Error('Expected the supplied six-slide reference');
await fs.mkdir(buildDir, { recursive: true });
const layouts = [];
for (const s of p.slides.items) layouts.push(JSON.parse(await (await s.export({ format: 'layout' })).text()));
console.log('Mapped source layouts');
const catalog = new Map();
for (let i = 0; i < layouts.length; i++) for (const el of layouts[i].elements) {
  const match = el.name?.match(/^Google Shape;(\d+);/);
  if (match) catalog.set(Number(match[1]), { ...el, slide: i });
}
const info = id => { const x = catalog.get(id); if (!x) throw new Error(`Missing template object ${id}`); return x; };
const get = id => p.resolve(info(id).id);
const set = (id, value) => { const x = info(id); if (x.kind !== 'textbox' && x.kind !== 'shape') throw new Error(`Not text: ${id}`); get(id).text = value; };
const map = values => Object.entries(values).forEach(([id, value]) => set(Number(id), value));
const normal = ids => ids.forEach(id => { get(id).text.bold = false; });
const boldLabels = (id, labels) => { normal([id]); labels.forEach(label => { get(id).text.get(label).bold = true; }); };
const addText = (slide, name, position, text, size, color = '#073DD0', bold = false, alignment = 'center') => {
  const shape = slide.shapes.add({ name, geometry: 'textbox', position, fill: 'none', line: { fill: 'none', width: 0 } });
  shape.text = text;
  shape.text.style = { typeface: 'Arial', fontSize: size, color, bold, alignment, verticalAlignment: 'middle', autoFit: 'none', insets: { left: 0, right: 0, top: 0, bottom: 0 } };
  return shape;
};
const replaceWithDiagramLabel = (id, label, size = 12, color = '#2453A6') => {
  const old = info(id); get(id).delete();
  return addText(p.slides.items[old.slide], `VAJRA diagram label ${id}`, old.position, label, size, color, true);
};

// Slide 1: preserve the template's bullet geometry and mixed emphasis.
get(64).text.replace('SIH26202', 'SIH26072');
get(64).text.replace('Ideas focused on the intelligent use of resources for transforming and advancements of technology with combining the artificial intelligence to explore more various sources and get valuable insights', 'AIML based Nowcasting of thunderstorm and lightning using atmospheric observation including multiple radars, satellite, lightning and model data.');
get(64).text.replace('Smart Automation', 'Disaster Management');

// Slide 2: problem, solution and a compact editable data-flow diagram.
console.log('Editing slide 2');
map({
  72: 'IDEA TITLE: VAJRA',
  76: 'Who needs it: Weather officers and people outdoors.\nProblem: Storm risk can change within a broad warning area. Local decisions need recent evidence, useful lead time and clear uncertainty.\nEvidence: India recorded 2,862 lightning deaths in 2020 [1]. Local forecast skill must be measured.',
  77: 'A local prediction model for the next 30 minutes.\nCombine radar, INSAT, lightning and weather context.\nEstimate risk and an onset window for each covered cell.\nShow data age, gaps and reasons to the officer.\nReview public rain reports before training use.\nResearch prototype. NCR accuracy is still unmeasured.',
  83: 'Accuracy and trust', 85: 'Cell', 87: '30-min forecast target', 89: 'Onset windows', 91: 'Fresh inputs', 93: 'Seasonal checks', 95: 'Scores', 97: 'Reviewed feedback', 128: 'No LLM needed',
  110: 'Weather observations to local guidance', 112: 'Sources', 113: 'India',
  115: 'Motion', 116: 'Echo movement + change', 118: 'Clouds', 119: 'Growth + moisture', 121: 'Labels', 122: 'Lightning + rain + coverage',
  124: 'Nowcast', 125: 'Risk + onset + evidence',
});
boldLabels(76, ['Who needs it:', 'Problem:', 'Evidence:']);
normal([77]);
get(77).text.underline = 'none';
const radar = get(80);
const radarFrame = info(80).position;
radar.replace({ blob: await fs.readFile('artifacts/observed-radar.png'), contentType: 'image/png', alt: 'Recorded historical French radar experiment, 19 December 2018. Not NCR observations.', fit: 'cover' });
radar.frame = radarFrame;
radar.crop = { left: 0.202, top: 0.410, right: 0.291, bottom: 0.333 };
addText(p.slides.items[1], 'Historical radar disclosure', { left: 744, top: 618, width: 497, height: 23 }, 'French radar demo. NCR validation pending.', 16, '#FFFFFF', true);

// Slide 3: retain all template routing, lanes, containers and review workflow.
console.log('Editing slide 3');
map({
  252: 'Observations', 253: 'Radar / IR / strikes', 257: 'QC', 258: 'Time / units / masks',
  260: 'Update on fresh inputs\nHold when evidence is stale', 265: 'Raw evidence', 266: 'Files + time + hashes', 267: 'Weather features',
  277: 'Radar motion', 278: 'Optical flow + persistence', 279: 'Echo movement baseline',
  282: 'Satellite', 283: 'Cloud-top evolution', 287: 'Environment', 288: 'CAPE / wind / humidity',
  289: 'Aligned\nhistory', 291: 'Temporal prediction',
  292: 'Compact ConvLSTM\nLightning + onset heads\nHeld-out calibration',
  294: 'Accuracy before public alerts', 295: 'Coverage + age + officer gate',
  296: '30 min', 297: 'target horizon', 298: '5 min', 299: 'onset bins',
  303: 'Forecast + evidence API', 313: 'Officer web dashboard', 314: 'Risk / reasons / data age', 317: 'Delivery: planned',
  330: 'React Native app', 331: 'Local view / rain reports\n12 Indian languages + English', 333: 'Research app',
  336: 'Officer review', 337: 'Evidence / skill / time', 339: 'Release?',
  341: 'NO /\nUNCERTAIN', 343: 'APPROVED', 345: 'Save reason', 346: 'Hold alert', 348: 'Issue alert',
  351: 'Local guidance', 352: 'Validated service only', 354: 'Expiry + delivery record',
  360: 'Versioned event store', 361: 'Forecasts / outcomes / coverage\nReview and model history', 363: 'read / write', 365: 'file\nreference',
  370: 'Weather archive', 371: 'Raw images + numeric fields\nSource and processing version',
  374: 'SQLite', 375: 'Research ledger', 376: 'Consented rain reports', 378: 'record / query',
  383: 'Reviewed labels', 386: 'Train + test + calibrate', 389: 'Approve model', 391: 'Matched + reviewed labels', 393: 'approved\nmodel version',
  394: 'Operator user flow', 398: 'Select a region', 399: 'Check coverage and source availability',
  404: 'Inspect observations', 405: 'Review radar, cloud changes and data age',
  410: 'Open the forecast', 411: 'Risk, onset range and no-event chance',
  416: 'Check the evidence', 417: 'Skill, sensor gaps and explanation',
  422: 'Approve or withhold', 423: 'Apply validation and authority rules',
  428: 'Record the outcome', 429: 'Save issue time, location and expiry.',
  430: 'Match later observations for evaluation.', 431: 'Public model alerts remain disabled in research.',
  147: 'xarray', 154: 'Flow', 155: 'Optical flow', 156: 'Masks', 157: 'QC / age',
  158: 'ConvLSTM', 159: 'Temporal model', 161: 'Calibration', 163: 'Event store',
  165: 'Raw archive', 169: 'Scorecards', 171: 'IMERG', 178: 'TTS / SMS',
});
replaceWithDiagramLabel(146, 'xr', 25);
replaceWithDiagramLabel(160, 'Cal', 17);
replaceWithDiagramLabel(162, 'DB', 19);
replaceWithDiagramLabel(168, 'CSI', 17);
replaceWithDiagramLabel(170, 'Rain', 14);
// These source icons describe cameras, running people and weapons. Substitute
// native labels within the same node footprints in the requested diagram.
[250, 251, 271, 272, 273, 274, 275, 276, 280, 281, 359].forEach(id => get(id).delete());
addText(p.slides.items[2], 'Observation node', { left: 28, top: 184, width: 56, height: 33 }, 'DATA', 16, '#0072BC', true);
addText(p.slides.items[2], 'Motion node', { left: 208, top: 155, width: 33, height: 27 }, 'dBZ', 12, '#103586', true);
addText(p.slides.items[2], 'Satellite node', { left: 207, top: 219, width: 34, height: 24 }, 'IR', 16, '#103586', true);
addText(p.slides.items[2], 'Archive node', { left: 423, top: 417, width: 42, height: 27 }, 'DB', 16, '#0072BC', true);

// Slide 4: same feasibility columns and native challenge/strategy table.
console.log('Editing slide 4');
map({
  465: 'Compact temporal model.\nOpen radar processing tools.\nIndian data access needed.',
  478: 'COMPUTE FEASIBILITY', 479: 'Start with one region.\nReuse observing networks.\nBound queues and cache inputs.',
  491: 'Evidence for officer review.\nClear stale-data warnings.\nVersioned forecast records.',
  503: 'PUBLIC-SERVICE FEASIBILITY', 504: 'Local language guidance.\nConsent for rain reports.\nCoarse location by default.',
  508: 'ACCURACY CHECKS', 510: 'Research gates before public model alerts',
  513: 'Matched NCR observations\nCPU / GPU research worker\nVersioned labels + coverage',
  519: 'Pilot with documented Indian data rights.', 520: 'Measure skill, latency and useful lead time.', 521: 'Scale only after independent evaluation.',
});
const risks = [
  ['CHALLENGES', 'STRATEGY'],
  ['Technical\nMissing or stale sensors', 'Quality and age masks. Preserve native resolution. Withhold a claim when coverage is unknown.'],
  ['Operational\nFalse or missed alerts', 'Test on separate storms. Compare baselines. Check reliability and officer thresholds.'],
  ['Social\nPrivacy and biased reports', 'Coarse cells and consent. Deduplicate reports. Review independent corroboration.'],
  ['Feasibility\nData access and compute', 'Obtain permissions. Start with one region and a compact model. Measure cost per update.'],
];
for (let r = 0; r < 5; r++) for (let c = 0; c < 2; c++) get(514).cells.set(r, c, risks[r][c]);
const accuracyFrame = info(509).position;
get(509).delete();
const gates = [
  ['1  Freeze available inputs', 'No future observations in a forecast'],
  ['2  Separate storm events', 'Train, validate, calibrate, then test'],
  ['3  Compare baselines', 'Persistence and motion on equal cases'],
  ['4  Check probabilities', 'Reliability, Brier, POD, FAR and CSI'],
  ['5  Run a shadow pilot', 'Test outages and useful warning time'],
];
for (let i = 0; i < gates.length; i++) {
  const y = accuracyFrame.top + 4 + i * 61;
  const box = p.slides.items[3].shapes.add({ name: `Accuracy gate ${i + 1}`, geometry: 'roundRect', position: { left: accuracyFrame.left + 4, top: y, width: 302, height: 47 }, fill: i === 4 ? '#F0FAF4' : '#F2F7FE', line: { fill: i === 4 ? '#08A65B' : '#0072BC', width: 1 } });
  addText(p.slides.items[3], `Accuracy gate ${i + 1} title`, { left: accuracyFrame.left + 13, top: y + 3, width: 284, height: 22 }, gates[i][0], 16, '#214E83', true);
  addText(p.slides.items[3], `Accuracy gate ${i + 1} detail`, { left: accuracyFrame.left + 13, top: y + 26, width: 284, height: 16 }, gates[i][1], 12, '#52687E');
  if (i < gates.length - 1) p.slides.items[3].shapes.add({ name: `Accuracy gate connector ${i + 1}`, geometry: 'downArrow', position: { left: 578, top: y + 48, width: 12, height: 12 }, fill: '#0072BC', line: { fill: 'none', width: 0 } });
}

// Slide 5: benefits and recorded measurements, never speculative accuracy.
console.log('Editing slide 5');
map({
  534: 'Support Weather\nOperators', 535: 'Potential impact: Bring forecast risk and sensor evidence into one review.', 536: 'Benefit: Shows where evidence supports action or needs caution.',
  538: 'Help Outdoor\nCommunities', 539: 'Potential impact: Give local guidance to farmers, schools and outdoor workers.', 540: 'Benefit: Aim for more preparation time, subject to verified skill.',
  542: 'Reuse Observing\nNetworks', 543: 'Potential impact: Combine existing radar, satellite and station data.', 544: 'Benefit: A regional pilot can share data and compute resources.',
  546: 'Improve Local\nPreparedness', 547: 'Potential impact: Show the place, onset window and alert expiry.', 548: 'Benefit: Local language speech and reviewed feedback improve access.',
  549: 'Observations', 550: 'Radar + INSAT', 551: 'Lightning labels', 552: 'Rain gauges', 553: 'Time + coverage',
  554: 'VAJRA', 555: 'Temporal model', 556: 'Risk + timing', 557: 'Quality masks', 558: 'Measured skill',
  559: 'Public guidance', 560: 'Officer approval', 561: 'Local language', 562: 'Clear expiry', 563: 'Reviewed reports',
  569: '30-min forecast target', 572: '6 onset bins\nof 5 minutes each',
  575: '12 Indian languages\n+ English',
  578: '2,862 lightning deaths\nIndia, 2020 [1]\nHistorical need, not a\nclaim of lives saved',
  582: 'One French radar case, 19 Dec 2018\nEcho >=20 dBZ. NCR skill is unmeasured.',
});
[535, 536, 539, 540, 543, 544, 547, 548].forEach(id => boldLabels(id, [info(id).text?.startsWith('Benefit:') ? 'Benefit:' : 'Potential impact:']));
replaceWithDiagramLabel(564, 'RADAR\nINSAT', 20);
replaceWithDiagramLabel(565, 'RISK\n+ TIME', 20);
replaceWithDiagramLabel(566, 'LOCAL\nALERT', 20);
const chartFrame = info(581).position;
get(581).delete();
p.slides.items[4].charts.add('line', {
  name: 'Historical radar CSI comparison', position: chartFrame,
  title: 'Radar CSI vs lead time', titleTextStyle: { typeface: 'Arial', fontSize: 14, bold: true, fill: '#172534' },
  categories: ['5', '10', '15', '20'],
  series: [
    { name: 'Motion', values: [0.710716, 0.584645, 0.555373, 0.508291], line: { fill: '#0072BC', width: 2 }, marker: { symbol: 'circle', size: 4 } },
    { name: 'Persistence', values: [0.637651, 0.550681, 0.506571, 0.488428], line: { fill: '#EF3E4E', width: 2 }, marker: { symbol: 'square', size: 4 } },
  ],
  hasLegend: true, legend: { position: 'bottom', textStyle: { typeface: 'Arial', fontSize: 10, fill: '#172534' } },
  xAxis: { title: { text: 'Lead time (minutes)', textStyle: { typeface: 'Arial', fontSize: 10 } }, textStyle: { typeface: 'Arial', fontSize: 10 }, majorGridlines: null },
  yAxis: { min: 0, max: 1, majorUnit: 0.2, numberFormatCode: '0.0', textStyle: { typeface: 'Arial', fontSize: 10 }, majorGridlines: { fill: '#DDE5ED', width: 0.5 } },
  chartFill: '#FFFFFF', chartLine: { fill: 'none', width: 0 },
});

// Slide 6: replace every source and the original detector metrics.
console.log('Editing slide 6');
map({
  596: 'Accuracy requires independent storm events', 597: 'Train / validation / calibration / test',
  598: 'Freeze input availability and target windows.\nCheck phase, sensor gaps and no-event outcomes.',
  599: 'Compare baselines on the same covered cells.', 600: 'Report POD, FAR, CSI, Brier and reliability.',
  601: 'NCR skill unmeasured. Public model warnings disabled.',
  605: 'Synthetic lightning smoke', 606: '30 September 2026, 20 training steps', 608: 'Two synthetic test events. Baseline wins.',
});
const metrics = [['Brier', '0.2361'], ['Baseline', '0.2158'], ['Skill', '-0.0939'], ['Test events', '2']];
for (let r = 0; r < 4; r++) for (let c = 0; c < 2; c++) get(607).cells.set(r, c, metrics[r][c]);
const statusFrame = info(602).position;
get(602).delete();
const status = p.slides.items[5].tables.add({ rows: 5, columns: 2, ...{ left: statusFrame.left, top: statusFrame.top, width: statusFrame.width, height: statusFrame.height }, columnWidths: [156, 121.32], values: [
  ['Observed-data gate', 'NCR status'], ['Radar sequences', 'Pending'], ['INSAT matching', 'Pending'], ['Lightning coverage', 'Pending'], ['Local field skill', 'Unmeasured'],
] });
status.borders.assign({ fill: '#C6D6E6', width: 0.6 });
for (let r = 0; r < 5; r++) for (let c = 0; c < 2; c++) {
  const cell = status.getCell(r, c); cell.fill = r === 0 ? '#23568F' : r % 2 ? '#EAF2FA' : '#FFFFFF';
  cell.text.style = { typeface: 'Arial', fontSize: r === 0 ? 13 : 14, color: r === 0 ? '#FFFFFF' : '#172534', bold: r === 0, verticalAlignment: 'middle', insets: { top: 3, bottom: 3, left: 5, right: 5 } };
}
const references = [
  [[610,611,612,613], '01  Lightning deaths: 2,862 in 2020 (S5)', 'MHA / NCRB, Rajya Sabha (2022)', 'Official historical count for India.', 'Does not estimate lives VAJRA could save.', 'https://www.mha.gov.in/MHA1/Par2017/pdfs/par2022-pdfs/RS27072022/1197.pdf'],
  [[615,616,617,618], '02  Existing Indian warning service (S2)', 'PIB / MoES, Damini (2022)', 'Damini already provides advance alerts.', 'VAJRA superiority remains unproven.', 'https://www.pib.gov.in/PressReleasePage.aspx?PRID=1813993'],
  [[620,621,622,623], '03  Indian observations (S3)', 'IMD, official data and API portal', 'Station, radar and warning information.', 'Numeric NCR radar access still needed.', 'https://mausam.imd.gov.in/'],
  [[625,626,627,628], '04  INSAT data and rights (S3)', 'ISRO MOSDAC data guidelines', 'Satellite observations and permitted use.', 'Confirm redistribution before any release.', 'https://www.mosdac.gov.in/look/DOCS/mosdac-data-guidelines_english.pdf'],
  [[630,631,632,633,634], '05  Indian lightning labels (S3)', 'INCOIS catalogue, IITM network', '2019 stroke location, time and attributes.', 'Metadata is not a matched training corpus.', 'Network coverage is required for negatives.', 'https://incois.gov.in/essdp/ViewMetadata?fileid=05f2bab9-054f-45cf-b77d-1eaf089252ff'],
  [[636,637,638,639,640], '06  Supplemental rain labels (S3)', 'NASA GPM IMERG V07', 'Half-hourly rain estimates at 0.1 degree.', 'Check latency and quality before use.', 'Not independent street-scale gauge truth.', 'https://www.earthdata.nasa.gov/data/catalog/ges-disc-gpm-3imerghh-07'],
  [[642,643,644,645], '07  Environmental model inputs (S3)', 'Open-Meteo forecast API', 'CAPE, humidity, wind and model rain.', 'Forecast context, not observed rain truth.', 'https://open-meteo.com/en/docs'],
  [[647,648,649,650], '08  Operational forecast context (S4)', 'IMD forecasting SOP', 'Warning practice and forecast definitions.', 'Compare only matched windows and areas.', 'https://mausam.imd.gov.in/imd_latest/contents/pdf/forecasting_sop.pdf'],
  [[652,653,654,655], '09  Temporal image model (S3)', 'Shi et al., ConvLSTM (2015)', 'Convolutional recurrence for nowcasting.', 'Architecture reference, not NCR evidence.', 'https://arxiv.org/abs/1506.04214'],
  [[657,658,659,660,661], '10  Radar quality control (S3)', 'wradlib radar workflow', 'Georeferencing and measurement checks.', 'Use physical values and quality masks.', 'Rendered tiles cannot replace calibrated dBZ.', 'https://docs.wradlib.org/en/2.0.0/notebooks/basics/wradlib_workflow.html'],
  [[663,664,665,666], '11  Lightning before first strike (S3)', 'ProbSevere LightningCast (2022)', 'Satellite-based probabilistic forecasting.', 'Transfer to INSAT requires local evaluation.', 'https://journals.ametsoc.org/view/journals/wefo/37/7/WAF-D-22-0019.1.xml'],
  [[668,669,670,671], '12  Time-to-event method (S3)', 'Gensheimer & Narasimhan (2019)', 'Discrete-time survival neural network.', 'Keep censoring and no-event outcomes.', 'https://peerj.com/articles/6257/'],
  [[673,674,675,676,677], '13  Active / break monsoon phase (S4)', 'IITM, active-break selection', 'Phase-aware calibration is a hypothesis.', 'Use only phase information known at issue.', 'Sparse phase data need a pooled fallback.', 'https://tropmet.res.in/erpas/files/active_break_selection.php'],
  [[679,680,681,682,683], '14  Seasonal Z-R in Delhi (S4)', 'Delhi radar study (2025)', 'Local Z-R calibration has prior research.', 'Fit on training gauges and test separately.', 'No claim of an unpublished first for Delhi.', 'https://doi.org/10.1016/j.pce.2025.104182'],
  [[685,686,687], '15  Reproducible project measurements (S5-6)', 'VAJRA repository, VALIDATION.md', 'French radar case and synthetic smoke only.', 'https://github.com/omansharora5/ps_2/blob/main/VALIDATION.md'],
  [[689,690,691,692], '16  Verification and weak labels (S3-6)', 'VAJRA public verification guide', 'Equal cohorts, calibration and reviewed reports.', 'No majority-to-truth or automatic promotion.', 'https://github.com/omansharora5/ps_2/blob/main/docs/PUBLIC_VERIFICATION_GUIDE.md'],
];
for (const row of references) {
  const [ids, ...rest] = row; const url = rest.pop();
  ids.forEach((id, index) => {
    set(id, rest[index]);
    // Text replacement preserves source formatting, including links. Point
    // every run in each reference card at its replacement weather source.
    get(id).text.get(rest[index]).link = { uri: url, isExternal: true };
    get(id).text.underline = index === 1 ? 'sng' : 'none';
  });
}

const notes = [
  `VAJRA, SIH26072. Problem metadata transcribed from the user's SIH26072_Detailed_Technical_Analysis.md. Ministry of Earth Sciences, India Meteorological Department. Core deliverable: a local predictive model. Website and React Native app are evidence and delivery clients. NCR is the proposed first scientific pilot. The template supplied no team ID.`,
  `The next 30 minutes is a design target, not a demonstrated reliable lead time. Broad warnings alone do not resolve every local decision. Damini already offers advance lightning alerts, so this deck makes no superiority claim. Sources: ${references[0].at(-1)} (27 July 2022, annexure: 2,862 deaths in India in 2020); ${references[1].at(-1)} (6 April 2022, Damini). Image: actual project screenshot artifacts/observed-radar.png, historical Meteo-France radar data from 19 December 2018. It does not show NCR weather. See VALIDATION.md and data/external/meteonet_manifest.json in this repository.`,
  `Proposed integrated architecture around implemented research components. Separate executable components include image motion experiments, compact ConvLSTM lightning classification, rain/first-lightning discrete-time survival heads, calibration, citizen evidence ledger, website and React Native app. Unified live sensor fusion, trusted NCR serving and authorised public alert publication remain to be established. Lightning event probabilities can use held-out calibration; timing distributions still need calibration and field validation. Five-minute bins are model targets, not source resolution. Only covered, event-free initial periods support onset predictions. Quality and age masks handle missing inputs. NWP context integration is proposed. No LLM or Jev is required. Public reports: neutral yes/no/unsure, consent, duplicate controls, closed reporting windows and independent review. Majority agreement creates a candidate weak rain-presence label, never sensor truth. Training runs remain versioned and require explicit promotion. New inputs update forecasts, not model weights. References 03-07, 09-12 and 16. ${references.map(r => r.at(-1)).join('\n')}`,
  `Accuracy plan: split by storm event and time; prevent input-arrival leakage; separate validation, calibration and untouched test events; compare persistence and motion on identical covered cohorts; report POD, false-alarm ratio, CSI, Brier, reliability and uncertainty. Evaluate onset with censoring, misses and no-event outcomes retained. Test outages, warm-top rain and dust separately. Seasonal Z-R and phase-conditioned calibration are research additions with no demonstrated NCR improvement yet. The Delhi study is prior work, not a new discovery by VAJRA. Warm-rain and dust flags are descriptive, not validated classifiers. Numeric NCR radar, aligned INSAT sequences, lightning coverage and suitable observed labels remain dependencies. Public model warnings remain disabled. Feasibility concerns shared compute and a public-service pilot, with no revenue model. Sources: ${references[3].at(-1)}; ${references[7].at(-1)}; ${references[12].at(-1)}; ${references[13].at(-1)}.`,
  `Benefits are intended pilot outcomes. We have not measured lives saved, farmer income improvement, latency improvement or carbon savings. Twelve Indian languages plus English and device TTS/SMS composer exist as prototype features; translations need review and this does not prove delivery infrastructure. Chart: recorded historical Meteo-France radar case, 19 December 2018, CSI for echoes at least 20 dBZ. Lead minutes [5,10,15,20]. Motion/translation CSI [0.710716,0.584645,0.555373,0.508291]; persistence CSI [0.637651,0.550681,0.506571,0.488428]. Source: repository VALIDATION.md and recorded historical radar evaluation. One case is not an operational accuracy estimate and is unrelated to lightning skill. Lightning deaths: 2,862 in India in 2020, MHA/NCRB parliamentary answer dated 27 July 2022, annexure ${references[0].at(-1)}.`,
  `Sources and limitations:\n${references.map(r => `${r[1]}\n${r.slice(2,-1).join(' ')}\n${r.at(-1)}`).join('\n\n')}\n\nSynthetic smoke: artifacts/regional-research/d95852635db7d3a663ea160588729f78a59c61607c0e300d5d377777bee46cbc/report.json. 20 training steps, 2 synthetic test events. Calibrated lightning Brier 0.23609189291330068; climatology Brier 0.2158203125; Brier skill -0.09392804680189992. Lower Brier is better; this model loses to the baseline. These are computation checks and do not validate lightning forecasts. The NCR status table distinguishes missing matched observations and unmeasured field skill. No operational IMD comparison has been established.`,
];
notes.forEach((text, i) => { p.slides.items[i].speakerNotes.clear(); p.slides.items[i].speakerNotes.textFrame.setText(text); });
console.log('Exporting candidate');

await fs.writeFile(path.join(buildDir, 'content.ndjson'), (await p.inspect({ kind: 'slide,textbox,shape,table,chart,image,notes', maxChars: 400000 })).ndjson);
const pptx = await PresentationFile.exportPptx(p);
await pptx.save(path.join(buildDir, 'candidate.pptx'));
for (let i = 0; i < p.slides.items.length; i++) {
  const slide = p.slides.items[i];
  const png = await p.export({ slide, format: 'png', scale: 1.25 });
  await fs.writeFile(path.join(buildDir, `slide-${i + 1}.png`), new Uint8Array(await png.arrayBuffer()));
  await fs.writeFile(path.join(buildDir, `slide-${i + 1}.json`), await (await slide.export({ format: 'layout' })).text());
  console.log(`Rendered VAJRA slide ${i + 1}`);
}
console.log(`Candidate: ${path.join(buildDir, 'candidate.pptx')}`);
