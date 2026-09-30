import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';

const runtime = process.env.CODEX_PRESENTATION_RUNTIME || 'C:/Users/dell/.cache/codex-runtimes/codex-primary-runtime/dependencies/node';
const python = process.env.CODEX_PRESENTATION_PYTHON || 'C:/Users/dell/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const source = 'presentations/VAJRA_SIH26072_v2.pptx';
const out = path.resolve('.presentation-build/revision3');
await fs.mkdir(out, { recursive: true });
execFileSync(python, ['scripts/restore_icon_architecture_canvas.py', source, 'presentations/VAJRA_SIH26072.pptx', path.join(out, 'style-base.pptx')], { stdio: 'inherit' });
const req = createRequire(path.join(runtime, 'package.json'));
const { FileBlob, PresentationFile } = await import(pathToFileURL(req.resolve('@oai/artifact-tool')));
const p = await PresentationFile.importPptx(await FileBlob.load(path.join(out, 'style-base.pptx')));
const s = p.slides.items[2];
const layout = JSON.parse(await (await s.export({ format: 'layout' })).text());
const byNumber = new Map();
for (const e of layout.elements) {
  const match = e.name?.match(/^Google Shape;(\d+);/);
  if (match) byNumber.set(Number(match[1]), e);
}
const get = n => p.resolve(byNumber.get(n).id);
const set = (n, value) => { get(n).text = value; };
const remove = n => get(n).delete();
const blue = '#073DD0', dark = '#123E7C';
const rect = (name, x, y, w, h, fill = 'none', stroke = 'none', geometry = 'rect', width = 1.7) => s.shapes.add({ name, geometry, position: { left: x, top: y, width: w, height: h }, fill, line: { fill: stroke, width: stroke === 'none' ? 0 : width } });
const text = (name, x, y, w, h, value, size = 11, color = blue) => {
  const el = rect(name, x, y, w, h);
  el.text = value;
  el.text.style = { typeface: 'Arial Narrow', fontSize: size, color, alignment: 'center', verticalAlignment: 'middle', autoFit: 'none', insets: { left: 0, right: 0, top: 0, bottom: 0 } };
  return el;
};
const line = (name, points, color = dark, dashed = false, width = 1.6, arrow = false) => {
  const x = Math.min(...points.map(v => v[0])), y = Math.min(...points.map(v => v[1]));
  const w = Math.max(1, Math.max(...points.map(v => v[0])) - x), h = Math.max(1, Math.max(...points.map(v => v[1])) - y);
  s.shapes.add({ name, geometry: 'custom', position: { left: x, top: y, width: w, height: h }, fill: 'none', line: { fill: color, width, style: dashed ? 'dashed' : 'solid' }, customPaths: [{ width: w, height: h, commands: points.map(([a, b], i) => ({ [i ? 'lineTo' : 'moveTo']: { x: a - x, y: b - y } })) }] });
  if (arrow) {
    const [a, b] = points.slice(-2), theta = Math.atan2(b[1] - a[1], b[0] - a[0]);
    const bx = b[0] - 6 * Math.cos(theta), by = b[1] - 6 * Math.sin(theta);
    line(`${name} head`, [[bx + 3 * Math.sin(theta), by - 3 * Math.cos(theta)], b, [bx - 3 * Math.sin(theta), by + 3 * Math.cos(theta)]], color, false, width);
  }
};
const grid = (name, x, y, size, color = dark) => {
  rect(name, x, y, size, size, '#EDF7FF', color, 'rect', 1.4);
  for (let j = 1; j < 3; j++) {
    line(`${name} row ${j}`, [[x, y + size * j / 3], [x + size, y + size * j / 3]], color, false, 1.2);
    line(`${name} column ${j}`, [[x + size * j / 3, y], [x + size * j / 3, y + size]], color, false, 1.2);
  }
};

console.log('Restoring reference icons, panels and operator sidebar');
const labels = {
  253: 'Radar / IR / strikes', 257: 'QC + align', 258: 'Time / units / age',
  260: '5-min source checks*\n10-min revisions*',
  278: 'Optical flow', 279: 'Persistence baseline', 287: 'Environment', 288: 'CAPE / wind / rain',
  292: 'Compact ConvLSTM\nLightning + onset heads\nQuality / age masks',
  294: 'Evidence checks', 295: 'Calibration / coverage / age',
  303: 'Forecast + evidence API', 313: 'Officer dashboard', 314: 'Risk / paths / data age',
  317: 'Delivery: planned', 330: 'React Native app',
  331: 'Local view / rain reports\n12 Indian languages + English', 333: 'Research app',
  337: 'Evidence / thresholds', 345: 'Save reason', 346: 'Hold alert', 348: 'Issue alert',
  351: 'Local guidance*', 352: 'Voice / SMS / relay*', 354: 'Signed alerts / expiry',
  360: 'Event ledger', 361: 'Forecasts / outcomes\nModel / review history',
  370: 'Weather archive', 371: 'Raw fields / source hashes',
  374: 'Feedback store', 375: 'Consent + review', 376: 'Weak rain reports',
  386: 'Train + evaluate', 391: 'Matched, reviewed outcomes',
  431: 'Research model alerts stay disabled.',
};
for (const [n, value] of Object.entries(labels)) set(Number(n), value);

// Replace placeholders with editable weather symbols in their existing footprints.
for (const name of ['Observation node', 'Motion node', 'Satellite node', 'Archive node']) {
  const e = layout.elements.find(v => v.name === name);
  if (e) p.resolve(e.id).delete();
}
rect('Weather observation cloud', 33, 183, 47, 27, '#0874ED', 'none', 'cloud');
rect('Weather observation lightning', 51, 201, 14, 20, '#0874ED', 'none', 'lightningBolt');
line('Weather observation rain 1', [[38, 211], [34, 218]], blue);
line('Weather observation rain 2', [[74, 211], [70, 218]], blue);

// Radar sweep in the first purple feature panel.
rect('Radar sweep disk', 211, 150, 27, 27, '#EDF4FF', dark, 'ellipse');
rect('Radar inner ring', 218, 157, 13, 13, 'none', dark, 'ellipse', 1.1);
line('Radar crosshair horizontal', [[213, 164], [236, 164]], dark, false, 1);
line('Radar crosshair vertical', [[224.5, 152], [224.5, 175]], dark, false, 1);
line('Radar sweep', [[224.5, 164], [234, 153]], blue, false, 2.4);
rect('Radar echo', 230, 168, 3.5, 3.5, blue, 'none', 'ellipse');

// Satellite with solar panels, using the reference's blue line-icon treatment.
rect('Satellite bus', 219, 217, 12, 14, '#EDF4FF', dark, 'roundRect');
grid('Satellite solar panel left', 207, 219, 10, dark);
grid('Satellite solar panel right', 233, 219, 10, dark);
line('Satellite antenna', [[224, 217], [229, 211], [232, 214]], dark);
line('Satellite downlink', [[224, 233], [229, 238], [233, 233]], blue, true, 1.2);

// Wind and thermometer replace the generic depth cube.
[284, 285, 286].forEach(remove);
line('Wind top', [[212, 279], [229, 279], [233, 276], [229, 273]], dark, false, 1.8);
line('Wind middle', [[210, 285], [237, 285]], dark, false, 1.8, true);
line('Wind lower', [[213, 291], [226, 291], [230, 294], [226, 297]], dark, false, 1.8);

// Ledger icon and a data grid inside the original archive folder.
for (let i = 0; i < 3; i++) {
  rect(`Ledger sheet ${i}`, 432 + i * 3, 414 + i * 5, 24, 15, '#E7FAFF', '#0072BC', 'roundRect', 1.3);
  line(`Ledger row ${i}`, [[437 + i * 3, 421 + i * 5], [449 + i * 3, 421 + i * 5]], '#0072BC', false, 1.1);
}
[368, 369].forEach(remove);
grid('Weather raster in folder', 565, 436, 24, '#0874ED');

// The approved checkpoint returns to the model, not to a feature card.
[244, 245, 392, 393].forEach(remove);
line('Approved checkpoint return', [[320, 471], [320, 409], [368, 409], [368, 326], [465, 326], [465, 315]], blue, true, 1.15, true);
text('Approved checkpoint label', 298, 345, 67, 33, 'approved\nmodel version', 11);

// Feedback must be reviewed and corroborated before it reaches the training corpus.
line('Reviewed citizen evidence loop', [[711, 552], [711, 563], [23, 563], [23, 493], [57, 493]], blue, true, 1.15, true);
text('Reviewed citizen evidence label', 318, 543, 278, 17, 'Review + corroborate weak rain reports', 11.5);
text('Deployment targets legend', 762, 557, 498, 19, '* Planned integration / NCR validation pending', 11.5, '#536A7E');

// Keep the complete bottom logo rail. Use native symbols for research modules.
for (const n of [154, 156, 158]) remove(n);
for (const oldId of [146, 160, 162, 168, 170]) {
  const e = layout.elements.find(v => v.name === `VAJRA diagram label ${oldId}`);
  if (e) p.resolve(e.id).delete();
}
grid('xarray grid symbol', 184, 592, 29);
for (let i = 0; i < 3; i++) line(`Optical flow vector ${i}`, [[456, 594 + i * 10], [481 + (i === 1 ? 5 : 0), 594 + i * 10]], '#2453A6', false, 1.7, true);
grid('Quality mask symbol', 519, 592, 29, '#6F42A8');
rect('Masked missing cell', 519, 592, 10, 10, '#6F42A8');
rect('Masked second cell', 539, 612, 9, 9, '#6F42A8');
for (const [x, y] of [[589, 598], [606, 591], [606, 607], [624, 598]]) rect(`Temporal node ${x}-${y}`, x, y, 6, 6, '#7841D8', 'none', 'ellipse');
for (const pts of [[[595, 601], [606, 594]], [[595, 601], [606, 610]], [[612, 594], [624, 601]], [[612, 610], [624, 601]]]) line('Temporal connection', pts, '#7841D8', false, 1.3);
line('Calibration axes', [[684, 591], [684, 620], [714, 620]], '#2453A6', false, 1.5);
line('Calibration diagonal', [[687, 617], [709, 595]], '#2453A6', true, 1);
line('Calibration curve', [[687, 616], [693, 613], [698, 603], [708, 598]], '#2453A6', false, 2);
rect('Event store symbol', 756, 590, 29, 32, '#EAFBFE', '#0072BC', 'can', 1.4);
for (let i = 0; i < 3; i++) rect(`Score bar ${i}`, 976 + i * 9, 617 - i * 7, 6, 5 + i * 7, '#2453A6');
rect('IMERG rain cloud', 1036, 589, 31, 20, '#298FCA', 'none', 'cloud');
for (let i = 0; i < 3; i++) line(`IMERG rain ${i}`, [[1042 + i * 8, 610], [1038 + i * 8, 620]], '#298FCA', false, 1.6);

const notes = (await p.inspect({ kind: 'notes', maxChars: 160000 })).ndjson.split('\n').filter(Boolean).map(v => JSON.parse(v)).find(v => v.kind === 'notes' && v.slideIndex === 2)?.text || '';
s.speakerNotes.clear();
s.speakerNotes.textFrame.setText(`${notes}\n\nRevision 3 restores the exact icon-led composition requested by the user: observation and QC icons, stacked purple weather feature panels, an orange model panel, FastAPI, monitor and phone symbols, officer release branches, evidence storage, a reviewed-learning loop, the six-step operator sidebar and the bottom technology logo rail. Weather icons and the research-module symbols are native editable shapes, not official new software logos. The approved-checkpoint return enters the temporal model. Citizen reports follow a separate review/corroboration route into reviewed weak evidence. The phone and dashboard branches are research views; public guidance requires a validated service and authorised release. The 5-minute source check and 10-minute revision cadences, public voice/SMS/relay delivery and optional decision classifier remain planned integrations. Bitchat-inspired BLE would relay signed unexpired alerts through compatible nearby peers. No LLM is required. Exact code, source and status details remain in presentations/SIH26072_ARCHITECTURE_AND_DATA_FLOW.md and presentations/REVISION_2_DESIGN.md.\n\nThis revision changes only slide 3. Slide 2's real NCR satellite backdrop and clearly labelled illustrative path, the value propositions, all evidence tables and the measured chart remain unchanged.`);

for (let i = 0; i < 6; i++) {
  const slide = p.slides.items[i];
  await fs.writeFile(path.join(out, `slide-${i + 1}.json`), await (await slide.export({ format: 'layout' })).text());
  const png = await p.export({ slide, format: 'png', scale: 1.25 });
  await fs.writeFile(path.join(out, `slide-${i + 1}.png`), new Uint8Array(await png.arrayBuffer()));
  console.log(`Rendered ${i + 1}`);
}
await (await PresentationFile.exportPptx(p)).save(path.join(out, 'candidate.pptx'));
execFileSync(python, ['scripts/restore_unchanged_presentation_chart.py', source, path.join(out, 'candidate.pptx')], { stdio: 'inherit' });
console.log('Saved icon-led architecture revision');
