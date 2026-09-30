import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';

const runtime = process.env.CODEX_PRESENTATION_RUNTIME || 'C:/Users/dell/.cache/codex-runtimes/codex-primary-runtime/dependencies/node';
const requireRuntime = createRequire(path.join(runtime, 'package.json'));
const { FileBlob, PresentationFile } = await import(pathToFileURL(requireRuntime.resolve('@oai/artifact-tool')));
const source = process.argv[2] || 'presentations/VAJRA_SIH26072.pptx';
const out = path.resolve('.presentation-build/revision2');
await fs.mkdir(out, { recursive: true });
const p = await PresentationFile.importPptx(await FileBlob.load(source));
if (p.slides.items.length !== 6) throw new Error('Expected six source slides');
console.log('Imported deck');
const layouts = [];
for (const s of p.slides.items) layouts.push(JSON.parse(await (await s.export({ format: 'layout' })).text()));
const notes = (await p.inspect({ kind: 'notes', maxChars: 150000 })).ndjson;
await fs.writeFile(path.join(out, 'source-notes.ndjson'), notes);
const C = { blue: '#073DD0', ink: '#174C7C', body: '#244461', purple: '#B48EFF', lavender: '#F2EBFF', orange: '#EEA03B', cream: '#FFF5E5', green: '#08A65B', mint: '#EDFAF2', cyan: '#00A5C8', ice: '#EAFBFE', line: '#315680', muted: '#536A7E' };
const rect = (s, name, x, y, w, h, fill = 'none', stroke = 'none', geometry = 'rect', dashed = false) => s.shapes.add({ name, geometry, position: { left: x, top: y, width: w, height: h }, fill, line: { fill: stroke, width: stroke === 'none' ? 0 : 1.1, style: dashed ? 'dashed' : 'solid' } });
const txt = (s, name, x, y, w, h, value, size = 16, color = C.body, bold = false, align = 'left') => {
  const sh = rect(s, name, x, y, w, h);
  sh.text = value;
  sh.text.style = { typeface: 'Arial', fontSize: size, color, bold, alignment: align, verticalAlignment: 'middle', autoFit: 'none', insets: { left: 0, top: 0, right: 0, bottom: 0 } };
  return sh;
};
const route = (s, name, points, color = C.line, dashed = false, arrow = true, width = 1.3) => {
  const xs = points.map(v => v[0]), ys = points.map(v => v[1]);
  const x = Math.min(...xs), y = Math.min(...ys), w = Math.max(1, Math.max(...xs) - x), h = Math.max(1, Math.max(...ys) - y);
  const commands = points.map(([px, py], i) => ({ [i ? 'lineTo' : 'moveTo']: { x: px - x, y: py - y } }));
  s.shapes.add({ name, geometry: 'custom', position: { left: x, top: y, width: w, height: h }, fill: 'none', line: { fill: color, width, style: dashed ? 'dashed' : 'solid' }, customPaths: [{ width: w, height: h, commands }] });
  if (arrow) {
    const [a, b] = points.slice(-2), angle = Math.atan2(b[1] - a[1], b[0] - a[0]);
    const back = [b[0] - 7 * Math.cos(angle), b[1] - 7 * Math.sin(angle)];
    const pts = [b, [back[0] + 3.5 * Math.sin(angle), back[1] - 3.5 * Math.cos(angle)], [back[0] - 3.5 * Math.sin(angle), back[1] + 3.5 * Math.cos(angle)], b];
    const ax = Math.min(...pts.map(v => v[0])), ay = Math.min(...pts.map(v => v[1]));
    const aw = Math.max(1, Math.max(...pts.map(v => v[0])) - ax), ah = Math.max(1, Math.max(...pts.map(v => v[1])) - ay);
    s.shapes.add({ name: `${name} arrow`, geometry: 'custom', position: { left: ax, top: ay, width: aw, height: ah }, fill: color, line: { fill: 'none', width: 0 }, customPaths: [{ width: aw, height: ah, commands: pts.map(([px, py], i) => ({ [i ? 'lineTo' : 'moveTo']: { x: px - ax, y: py - ay } })) }] });
  }
};
const box = (s, name, x, y, w, h, title, body, fill = C.lavender, stroke = C.purple, opts = {}) => {
  const sh = rect(s, name, x, y, w, h, fill, stroke, opts.geometry || 'roundRect', opts.dashed);
  const compact = h <= 64;
  const pad = opts.geometry === 'can' ? 18 : compact ? 5 : 10;
  const detailOffset = compact ? 24 : 28;
  txt(s, `${name} heading`, x + 10, y + pad, w - 20, compact ? 20 : 23, title, opts.titleSize || 17, C.blue, true, opts.align || 'left');
  txt(s, `${name} detail`, x + 10, y + pad + detailOffset, w - 20, h - pad - detailOffset - 4, body, opts.bodySize || 14.5, C.body, false, opts.align || 'left');
  return sh;
};

console.log('Revising slide 2');
const s2 = p.slides.items[1];
for (const e of layouts[1].elements) {
  if (e.name?.startsWith('Google Shape;121;')) p.resolve(e.id).text = 'History';
  if (e.name?.startsWith('Google Shape;122;')) p.resolve(e.id).text = 'Past rain / strikes / coverage';
}
for (const e of layouts[1].elements) {
  if (e.position.left >= 729 && e.position.top >= 88 && e.position.top < 665) p.resolve(e.id).delete();
}
rect(s2, 'Value proposition frame', 729.65, 88.89, 529.98, 277, '#FFFFFF', '#B8CCDC');
txt(s2, 'Key Value Proposition', 744, 100, 497, 31, 'Key Value Proposition', 24, '#23568F', true);
const features = [
  ['30-min Outlook', '5-min Refresh*', '10-min Updates*', 'Rolling Forecasts*', 'Lightning Lead', 'Onset Windows', 'Monsoon-aware', 'Seasonal Z-R'],
  ['Warm-rain Checks', 'Dust Flags', 'Evidence Cards', 'Public Scorecards*', 'Local Heatmaps*', 'Citizen Feedback', 'Reviewed Learning', 'Model Benchmarks*'],
  ['Native App', '12 Languages', 'Voice Alerts*', 'Offline Relay*', 'Open Stack', 'Graceful Fallback*', 'Compact Models', 'Decision Research*'],
];
for (let col = 0; col < 3; col++) for (let row = 0; row < 8; row++) {
  const x = 744 + col * 169, y = 139 + row * 25;
  rect(s2, `Feature marker ${col}-${row}`, x, y + 8, 4, 4, col === 0 ? C.blue : col === 1 ? C.purple : C.green, 'none', 'ellipse');
  txt(s2, `Feature ${col}-${row}`, x + 10, y, 156, 22, features[col][row], 15.7, '#172534');
}
txt(s2, 'Feature status legend', 744, 342, 500, 17, '* Deployment target / research hypothesis. See notes for status.', 11.8, C.muted);

rect(s2, 'NCR satellite frame', 729.65, 374, 529.98, 284.6, '#FFFFFF', '#B8CCDC');
const frame = { left: 741, top: 385, width: 506, height: 235 };
s2.images.add({ name: 'Observed Delhi NCR VIIRS satellite image', blob: await fs.readFile('presentations/assets/ncr-viirs-2024-06-27.png'), contentType: 'image/png', position: frame, fit: 'contain', alt: 'NASA GIBS Suomi-NPP VIIRS daily true-color satellite mosaic over Delhi NCR, 27 June 2024. Overlaid path and rainfall changes are an illustrative scenario, not measured motion or a model output.' });
rect(s2, 'Satellite title background', 741, 385, 506, 27, '#0B223A');
txt(s2, 'Satellite title', 749, 388, 490, 21, 'DELHI NCR / VIIRS / 27 JUN 2024', 13.3, '#FFFFFF', true);
// Editable map annotations use the same EPSG:3857 image bounds as the source.
const point = (fx, fy) => [frame.left + fx * frame.width, frame.top + fy * frame.height];
const dwarka = point(0.4313043478260987, 0.4216082801341908);
rect(s2, 'Dwarka sample cell', dwarka[0] - 12, dwarka[1] - 12, 25, 25, 'none', '#FFFFFF', 'rect', true);
rect(s2, 'Dwarka marker', dwarka[0] - 4, dwarka[1] - 4, 8, 8, '#FFDA48', '#FFFFFF', 'ellipse');
rect(s2, 'Dwarka label background', dwarka[0] + 15, dwarka[1] - 8, 128, 35, '#0B223A');
txt(s2, 'Dwarka label', dwarka[0] + 21, dwarka[1] - 6, 119, 30, 'Dwarka\nsample research cell', 11.8, '#FFFFFF');
for (const [label, fx, fy] of [['Delhi', 0.5730434782608752, 0.3752043358597097], ['Gurugram', 0.4144347826087057, 0.7036565926621395], ['Noida', 0.7313043478260914, 0.5420433499609868]]) {
  const [x, y] = point(fx, fy);
  rect(s2, `${label} marker`, x - 2, y - 2, 4, 4, '#FFFFFF', 'none', 'ellipse');
  const lx = label === 'Delhi' ? x + 7 : x + 6, ly = label === 'Delhi' ? y - 21 : y + 2;
  rect(s2, `${label} backplate`, lx, ly, label === 'Gurugram' ? 68 : 44, 17, '#0B223A');
  txt(s2, `${label} map label`, lx + 3, ly, label === 'Gurugram' ? 63 : 40, 17, label, 11.5, '#FFFFFF');
}
const approach = [[776, 530], [813, 513], [854, 496], [dwarka[0] - 10, dwarka[1] + 4]];
route(s2, 'Illustrative cloud approach', approach, '#FFE34D', true, true, 2.5);
for (const [x, y, lead, rain, color] of [[776, 530, '+10 min', 'Light', '#35C5DC'], [826, 508, '+20 min', 'Moderate', '#FFA52E'], [dwarka[0] - 18, dwarka[1] + 9, '+30 min', 'Heavy', '#F76769']]) {
  rect(s2, `Scenario ${lead} rain area`, x - 9, y - 5, 23, 13, 'none', color, 'ellipse', true);
  rect(s2, `${lead} backplate`, x - 10, y + 17, 75, 31, '#0B223A');
  txt(s2, `${lead} scenario label`, x - 6, y + 18, 69, 29, `${lead}\n${rain}`, 10.8, color, true);
}
rect(s2, 'Forecast illustration banner', 741, 592, 506, 28, '#0B223A');
txt(s2, 'Forecast illustration text', 749, 594, 490, 24, 'ILLUSTRATIVE PATH + RAIN CHANGES', 12.5, '#FFE34D', true);
txt(s2, 'Satellite provenance caption', 742, 625, 508, 26, 'NASA observed backdrop. Overlay is a scenario, not a forecast result.', 12.2, '#96352F', false);

console.log('Rebuilding slide 3 weather architecture');
const s3 = p.slides.items[2];
for (const e of layouts[2].elements) if (e.position.top > 95 && e.position.top < 667) p.resolve(e.id).delete();
txt(s3, 'Forecast loop label', 25, 111, 1220, 26, 'FORECAST LOOP     5-min source checks* / 10-min revisions* / rolling 30-min outlook', 17, C.ink, true);
// Routes are separate editable native paths, kept clear of labels.
route(s3, 'Sources to alignment', [[217, 213], [244, 213]]);
route(s3, 'Alignment to model', [[431, 213], [460, 213]]);
route(s3, 'Model to evidence', [[747, 213], [777, 213]]);
route(s3, 'Evidence to officer', [[964, 213], [998, 213]]);
route(s3, 'Source manifest archive', [[338, 279], [338, 318], [475, 318], [475, 348], [494, 348]]);
route(s3, 'Issued forecast archive', [[615, 290], [615, 340]]);
route(s3, 'Officer to release', [[1120, 282], [1120, 300]]);
route(s3, 'Release to public', [[1120, 360], [1120, 383]], C.green);
route(s3, 'Release hold', [[1068, 330], [1016, 330]], '#ED495A');
route(s3, 'Public reports', [[998, 428], [965, 428]]);
route(s3, 'Peer relay', [[1120, 467], [1120, 484]], C.blue, true);
route(s3, 'Archive to matching', [[480, 394], [436, 394]]);
route(s3, 'Reports to reviewed labels', [[871, 466], [871, 480], [339, 480], [339, 449]]);
route(s3, 'Reviewed labels to corpus', [[242, 407], [128, 407], [128, 515]]);
route(s3, 'Corpus to train', [[225, 562], [267, 562]], C.blue);
route(s3, 'Train to verification', [[486, 562], [524, 562]], C.blue);
route(s3, 'Verify to promote', [[750, 562], [794, 562]], C.blue);
route(s3, 'Approved model return', [[879, 515], [879, 497], [759, 497], [759, 311], [715, 311], [715, 290]], C.blue, true);
route(s3, 'Verification scorecard', [[639, 606], [639, 621], [983, 621], [983, 574], [998, 574]], C.blue, true);
route(s3, 'Shadow decision features', [[869, 281], [869, 300]], C.purple, true);

box(s3, 'Weather inputs', 25, 150, 192, 129, 'Weather inputs', 'Radar: dBZ / velocity\nINSAT: clouds / moisture\nLightning + coverage\nGauges + NWP context', C.lavender, C.purple, { bodySize: 14.2 });
box(s3, 'Alignment and quality', 244, 150, 187, 129, 'Align + check', 'UTC / units / alignment\nQuality / age / masks\nValidated fallback\nWithhold poor inputs', C.lavender, C.purple, { bodySize: 14.1 });
box(s3, 'Prediction model', 460, 144, 287, 146, 'Regional prediction model', 'Motion + cloud growth + CAPE\nCompact ConvLSTM / 3 heads\nLightning risk + onset windows\nRain motion baseline / 30 min', C.cream, C.orange, { bodySize: 16 });
box(s3, 'Evidence gate', 777, 157, 187, 124, 'Evidence gate', 'Coverage + source age\nPhase calibration, if valid\nSkill + officer thresholds\nHold on weak evidence', C.cream, C.orange, { bodySize: 14.1 });
box(s3, 'Officer review', 998, 151, 244, 131, 'Officer web dashboard', 'Local heatmap + tracked path\nRisk / data age / reasons\nThreshold + authorised review', '#EFF7FF', '#6AA8DB', { bodySize: 15 });
rect(s3, 'Release decision', 1068, 300, 104, 60, '#EFF7FF', C.blue, 'diamond');
txt(s3, 'Release decision label', 1084, 315, 73, 29, 'Release?', 15, C.blue, true, 'center');
rect(s3, 'Hold alert box', 987, 318, 30, 25, '#FFF1F3', '#ED495A', 'roundRect');
txt(s3, 'Hold label', 978, 346, 51, 21, 'Hold', 12.5, '#ED495A', true, 'center');
txt(s3, 'No label', 1032, 308, 27, 17, 'No', 12, '#ED495A');
txt(s3, 'Yes label', 1131, 362, 66, 17, 'Approved', 12, C.green);
box(s3, 'Native mobile app', 998, 383, 244, 84, 'React Native app', 'Local view / 12 languages + English\nVoice + SMS alert delivery*', '#EFF7FF', '#6AA8DB', { bodySize: 13.5 });
box(s3, 'Offline relay', 998, 484, 244, 50, 'Bitchat-inspired relay*', 'Signed, unexpired alerts / nearby peers', C.mint, C.green, { dashed: true, titleSize: 15.5, bodySize: 12 });
box(s3, 'Citizen observations', 778, 391, 187, 75, 'Citizen observations', 'Rain? yes / no / unsure\nConsent + duplicate checks', C.lavender, C.purple, { bodySize: 13.5 });
box(s3, 'Immutable evidence archive', 480, 340, 262, 104, 'Immutable evidence', 'Source / issue time / model version\nForecast revisions + later outcomes', C.ice, C.cyan, { geometry: 'can', align: 'center', bodySize: 14.1 });
box(s3, 'Reviewed outcomes', 242, 363, 194, 86, 'Reviewed outcomes', 'Gauge / strike coverage\nReview public weak labels', C.lavender, C.purple, { bodySize: 13.7 });
box(s3, 'Shadow classifier', 778, 300, 186, 64, 'Decision classifier*', 'Shadow hypothesis only\nNo public alert authority', C.lavender, C.purple, { dashed: true, titleSize: 15.5, bodySize: 12.5 });
txt(s3, 'Learning loop label', 267, 484, 430, 23, 'REVIEWED LEARNING', 16.5, C.ink, true);
box(s3, 'Matched corpus', 25, 515, 200, 91, 'Matched storm events', 'Freeze train / validation /\ncalibration / test partitions', C.ice, C.cyan, { geometry: 'can', titleSize: 16, bodySize: 13.5, align: 'center' });
box(s3, 'Candidate training', 267, 515, 219, 94, 'Train + recalibrate', 'Bounded offline worker\nMonsoon + seasonal Z-R\nTrain candidate checkpoints', C.cream, C.orange, { bodySize: 14.1 });
box(s3, 'Independent evaluation', 524, 515, 226, 94, 'Independent verification', 'POD / FAR / CSI / Brier\nBaseline + same-case tests\nReliability + useful lead time', C.cream, C.orange, { titleSize: 16.2, bodySize: 14.1 });
box(s3, 'Model promotion', 794, 515, 170, 94, 'Review candidate', 'Promote or retain\nVersioned checkpoint\nNo automatic release', C.mint, C.green, { titleSize: 16, bodySize: 13.7 });
box(s3, 'Public scorecard', 998, 548, 244, 58, 'Monthly scorecard*', 'Matched cases / reliability / data gaps', '#EFF7FF', '#6AA8DB', { titleSize: 15.5, bodySize: 12.6 });
txt(s3, 'Architecture status', 25, 634, 1218, 17, 'Research modules exist. Live NCR integration and * capabilities are proposed. Public model alerts remain disabled.', 13.2, '#96352F');
txt(s3, 'Architecture stack', 25, 651, 1218, 14, 'Python / PyTorch / OpenCV / xarray / FastAPI / React / React Native / SQLite     No LLM required', 11.7, C.muted);
// Native device symbols retain the visual vocabulary of the reference diagram.
rect(s3, 'Officer monitor', 1207, 164, 24, 17, '#DDF3FF', C.ink, 'roundRect');
route(s3, 'Monitor stand', [[1219, 181], [1219, 186]], C.ink, false, false, 2);
route(s3, 'Monitor base', [[1211, 186], [1227, 186]], C.ink, false, false, 2);
rect(s3, 'Native phone', 1213, 392, 16, 26, '#FFFFFF', C.ink, 'roundRect');
rect(s3, 'Phone screen', 1216, 397, 10, 15, '#DDF3FF');
rect(s3, 'Phone button', 1220, 414, 2, 2, C.ink, 'none', 'ellipse');

const s2notes = `Revision 2: the heading is Key Value Proposition. Labels describe research capabilities and deployment targets, not established NCR skill. Asterisks mark planned delivery, integration, benchmarks or hypotheses. The compact architecture aims to control compute cost, which has not yet been measured in a live NCR pilot. Five minutes is a source-check target, ten minutes is a revision target, and 30 minutes is the forecast horizon. Actual source cadence and publication latency vary. New evidence revises subsequent forecasts, while retaining prior issue times for evaluation.\n\nThe NASA GIBS Suomi-NPP VIIRS corrected-reflectance daily mosaic dated 27 June 2024 covers Delhi NCR. The exact overpass time is not established. The Dwarka rectangle is a sample research cell, not an administrative boundary. The approach arrow, +10/+20/+30 minute steps and light/moderate/heavy labels are illustrative overlays. A single true-color image cannot establish motion, rainfall intensity or future weather. This is a visual explanation, not a model forecast or evidence of forecast accuracy. Asset: presentations/assets/ncr-viirs-2024-06-27.png. Provenance and complete URL: presentations/assets/README.md and corresponding JSON. NASA GIBS documentation: https://nasa-gibs.github.io/gibs-api-docs/access-basics/ . Worldview: https://worldview.earthdata.nasa.gov/?v=76.55,28.32,77.70,28.79&l=VIIRS_SNPP_CorrectedReflectance_TrueColor&t=2024-06-27 .\n\nLightning lead and onset timing are research model heads awaiting independent Indian validation. Phase calibration currently applies to lightning probabilities with a pooled fallback. Onset hazards require their own calibration. Seasonal Z-R and monsoon research are not claimed as first inventions. Public monthly scorecards and comparable Google/IMD benchmarks are planned. Damini already provides advance location-based lightning alerts, valid for the next 40 minutes according to https://www.pib.gov.in/PressReleasePage.aspx?PRID=1813993 . No claim of superiority is made.\n\nThe React Native app has research views, language support, installed-device TTS and a user-triggered SMS composer. Automatic alert delivery and Bitchat integration are proposed. A Bitchat-inspired BLE relay needs compatible nearby peers and a connected gateway for fresh external alerts. It would relay approved, signed, unexpired messages with deduplication, cancellation and issuer verification. Reference: https://github.com/permissionlesstech/bitchat and WHITEPAPER.md. No interoperability or guaranteed offline reach is claimed. Citizen majority is weak corroborative evidence, never automatic ground truth. Detailed feature statuses: presentations/REVISION_2_DESIGN.md.\n\nHistorical need on the left: NCRB reported 2,862 lightning deaths in India in 2020, as reported in the Ministry of Home Affairs parliamentary reply: https://www.mha.gov.in/MHA1/Par2017/pdfs/par2022-pdfs/RS27072022/1197.pdf . This is not a claim of lives saved.`;
const s3notes = `Revision 2 redesigns the weather architecture while retaining the reference's blue connectors, pastel processing boxes, cylinders and decision diamond. The top lane is the proposed deployment flow. The lower lane trains and evaluates candidates from reviewed outcomes. These loops run on different timescales. Fast source checks and forecast revisions do not imply retraining every five or ten minutes.\n\nThe four inputs preserve native support, source timestamp, coverage, quality, missingness and acquisition availability. IMD raw radar, INSAT and lightning feeds require actual access. Open alternatives are source-specific. A satellite-only fallback is usable only after independent validation in that input regime. Missing sensors never become negative lightning labels. The motion branch estimates echo displacement and rain evolution. The compact ConvLSTM research model has three heads: binary lightning event, rain-onset hazards and first-lightning-onset hazards in six five-minute bins. Source: nowcast/regional_heads.py and scripts/train_regional_heads.py. Cloud growth and environmental context are input features to be assembled from time-aligned observations.\n\nThe current API research runs are synthetic or historical French radar replay (nowcast/service.py). The regional model is a separate training/research path, not a live NCR serving loop. The regional endpoint explicitly reports unavailable data where no qualifying feed exists. LatestForecastQueue bounds ticket metadata and rejects superseded/expired outputs. It is not a live provider scheduler. Five-minute checks and ten-minute revisions are deployment targets.\n\nThe evidence gate checks support, age, held-out skill and operational thresholds. Phase calibration only applies where fitted and validated. Current research decision policy always disables public dispatch (nowcast/decision_policy.py). A future authorised officer may approve an eligible operational alert or hold it. The optional decision classifier runs as a shadow hypothesis and cannot bypass these gates. No LLM/Jev is necessary.\n\nThe immutable archive is a logical boundary across raw files, manifests, forecast records and the SQLite review/operations ledger, not a claim that all raw arrays live inside SQLite. Keep every issue time, source hash, model version and revision. Match later sensor outcomes and coverage. Public reports require consent, deduplication, closed windows and independent corroboration. Keep accepted rain reports labelled weak evidence. They do not establish lightning truth.\n\nFreeze separate storm-event train, validation, calibration and test partitions. Train with bounded offline workers, verify against persistence/motion on identical cases, evaluate reliability and useful lead time, and compare advanced models only when available on matched support. The existing daily learning tick can queue candidates from eligible observed events. It never promotes a model automatically. Independently review candidate checkpoints before deployment. Source files include nowcast/operation_recipes.py, nowcast/operation_store.py, scripts/run_operations.py, nowcast/regional_science.py and nowcast/public_verification.py.\n\nThe React Native research client supports 12 Indian languages plus English, device TTS and a user-triggered SMS composer. Alert transport, monthly publication and Bitchat-inspired relay remain proposed. BLE requires compatible nearby peers, radio access and a relay path. A connected gateway is needed to introduce fresh alerts. Proposed controls: approved signed payload, expiry, deduplication, cancellation and issuer verification. Reference: https://github.com/permissionlesstech/bitchat/blob/main/WHITEPAPER.md .\n\nArchitecture and implementation mapping: presentations/SIH26072_ARCHITECTURE_AND_DATA_FLOW.md and presentations/REVISION_2_DESIGN.md.`;
for (const [s, text] of [[s2, s2notes], [s3, s3notes]]) { s.speakerNotes.clear(); s.speakerNotes.textFrame.setText(text); }

console.log('Rendering revision');
for (let i = 0; i < 6; i++) {
  const s = p.slides.items[i];
  await fs.writeFile(path.join(out, `slide-${i + 1}.json`), await (await s.export({ format: 'layout' })).text());
  const png = await p.export({ slide: s, format: 'png', scale: 1.25 });
  await fs.writeFile(path.join(out, `slide-${i + 1}.png`), new Uint8Array(await png.arrayBuffer()));
  console.log(`Rendered ${i + 1}`);
}
await (await PresentationFile.exportPptx(p)).save(path.join(out, 'candidate.pptx'));
// The import/export runtime preserves chart formula references but drops their
// embedded workbook. Restore the unchanged chart bundle from the source deck.
const python = process.env.CODEX_PRESENTATION_PYTHON || 'C:/Users/dell/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
execFileSync(python, ['scripts/restore_unchanged_presentation_chart.py', source, path.join(out, 'candidate.pptx')], { stdio: 'inherit' });
console.log('Saved revision candidate');
