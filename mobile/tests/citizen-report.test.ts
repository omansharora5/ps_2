import test from 'node:test';
import assert from 'node:assert/strict';
import { createReportController, prepareCitizenReport, REPORT_LIMITS, type ReportPhase, type SmsComposer } from '../src/lib/citizen-report.ts';
import { LANGUAGES, dictionaries } from '../../shared/translations.ts';
import { REPORT_COPY_KEYS } from '../../shared/report-translations.ts';

const draft = { manualPlace: '  Rampur village, north fields  ', note: 'Thunder heard at 15:10.\nOutdoor workers moved indoors.' };
function harness(result = 'unknown') {
  const calls: { recipients: string[]; body: string }[] = [];
  const phases: ReportPhase[] = [];
  let checks = 0;
  const engine: SmsComposer = {
    isAvailableAsync: async () => { checks++; return true; },
    sendSMSAsync: async (recipients, body) => { calls.push({ recipients, body }); return { result }; },
  };
  return { engine, calls, phases, checks: () => checks, controller: createReportController(engine, value => phases.push(value)) };
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(done => { resolve = done; });
  return { promise, resolve };
}

test('report preview is localized, manual, unverified and has no implicit location or practice warning', () => {
  const body = prepareCitizenReport(draft, 'en');
  assert.ok(body);
  assert.ok(body.startsWith('Unverified citizen observation'));
  assert.ok(body.includes('Locality: Rampur village, north fields'));
  assert.ok(body.includes(draft.note));
  assert.ok(body.endsWith('This is not an official warning. Please verify this observation.'));
  assert.doesNotMatch(body, /Patna|25\.5941|85\.1376|Practice message/);
  assert.equal(prepareCitizenReport({ manualPlace: '', note: 'Thunder' }, 'en'), null);
  assert.equal(prepareCitizenReport({ manualPlace: 'Place', note: ' \n ' }, 'en'), null);
  assert.equal(prepareCitizenReport({ manualPlace: 'x'.repeat(REPORT_LIMITS.place + 1), note: 'Thunder' }, 'en'), null);
  assert.equal(prepareCitizenReport({ manualPlace: 'Place', note: 'x'.repeat(REPORT_LIMITS.note + 1) }, 'en'), null);
  for (const { code } of LANGUAGES) {
    for (const key of REPORT_COPY_KEYS) {
      assert.doesNotMatch(dictionaries[code][key], /\uFFFD|\?{2,}/);
      if (code !== 'en') assert.notEqual(dictionaries[code][key], dictionaries.en[key], `${code}.${key}`);
    }
    const translated = prepareCitizenReport(draft, code)!;
    assert.ok(translated.startsWith(dictionaries[code].reportUnverified));
    assert.ok(translated.endsWith(dictionaries[code].reportNotOfficial));
  }
});

test('constructing, preparing or invalidating a report never opens a composer', async () => {
  const h = harness();
  prepareCitizenReport(draft, 'en');
  assert.equal(h.checks(), 0);
  assert.equal(h.calls.length, 0);
  assert.deepEqual(h.phases, []);
  await h.controller.open({ manualPlace: '', note: '' }, 'en');
  assert.equal(h.checks(), 0);
  assert.equal(h.calls.length, 0);
  assert.deepEqual(h.phases, ['invalid']);
});

test('explicit action opens the exact preview with no recipients and does not report delivery', async () => {
  for (const [result, expected] of [['sent', 'accepted'], ['cancelled', 'cancelled'], ['unknown', 'unknown'], ['unexpected', 'unknown']] as const) {
    const h = harness(result);
    await h.controller.open(draft, 'hi');
    assert.equal(h.checks(), 1);
    assert.deepEqual(h.calls, [{ recipients: [], body: prepareCitizenReport(draft, 'hi') }]);
    assert.deepEqual(h.phases, ['checking', 'composing', expected]);
  }
});

test('unavailable SMS does not open composer and an explicit retry can work', async () => {
  const h = harness();
  h.engine.isAvailableAsync = async () => false;
  await h.controller.open(draft, 'en');
  assert.deepEqual(h.phases, ['checking', 'unavailable']);
  assert.equal(h.calls.length, 0);
  h.engine.isAvailableAsync = async () => true;
  await h.controller.open(draft, 'en');
  assert.equal(h.calls.length, 1);
});

test('duplicate taps during both lookup and composer produce one launch', async () => {
  const h = harness();
  const available = deferred<boolean>();
  const response = deferred<{ result: string }>();
  h.engine.isAvailableAsync = () => available.promise;
  h.engine.sendSMSAsync = (recipients, body) => { h.calls.push({ recipients, body }); return response.promise; };
  const first = h.controller.open(draft, 'en');
  await h.controller.open(draft, 'en');
  available.resolve(true);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(h.calls.length, 1);
  await h.controller.open(draft, 'en');
  assert.equal(h.calls.length, 1);
  response.resolve({ result: 'unknown' });
  await first;
});

test('leaving the screen during availability check prevents a delayed composer launch', async () => {
  const h = harness();
  const available = deferred<boolean>();
  h.engine.isAvailableAsync = () => available.promise;
  const pending = h.controller.open(draft, 'en');
  h.controller.cancelPending();
  available.resolve(true);
  await pending;
  assert.equal(h.calls.length, 0);
  assert.deepEqual(h.phases, ['checking', 'idle']);
});

test('never-resolving availability fails after a deadline and late success cannot launch', async () => {
  const h = harness();
  const available = deferred<boolean>();
  h.engine.isAvailableAsync = () => available.promise;
  const controller = createReportController(h.engine, next => h.phases.push(next), { availabilityTimeoutMs: 8 });
  await controller.open(draft, 'en');
  assert.deepEqual(h.phases, ['checking', 'error']);
  available.resolve(true);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(h.calls.length, 0);
});

test('composer exceptions retain an error outcome and permit user retry', async () => {
  const h = harness();
  h.engine.sendSMSAsync = async () => { throw new Error('Native composer failed'); };
  await h.controller.open(draft, 'en');
  assert.deepEqual(h.phases, ['checking', 'composing', 'error']);
  h.engine.sendSMSAsync = async () => ({ result: 'cancelled' });
  await h.controller.open(draft, 'en');
  assert.equal(h.phases.at(-1), 'cancelled');
});
