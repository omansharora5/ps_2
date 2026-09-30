import test from 'node:test';
import assert from 'node:assert/strict';
import { createSpeechController, selectVoice, type SpeechEngine, type SpeechState } from '../src/lib/speech-controller.ts';

const hindi = { identifier: 'hindi-device', language: 'hi-IN', name: 'Hindi device voice' };
function harness(overrides: Partial<SpeechEngine> = {}) {
  const said: string[] = []; const states: SpeechState[] = []; let stops = 0;
  const engine: SpeechEngine = { stop: async () => { stops++; }, getAvailableVoicesAsync: async () => [hindi], speak: (text, options) => { said.push(text); options.onStart(); }, ...overrides };
  const controller = createSpeechController(engine, state => states.push(state));
  return { controller, said, states, stopCount: () => stops };
}
test('uses a matching installed voice, never silently substitutes English', async () => {
  assert.equal(selectVoice([hindi], 'hi-IN')?.identifier, hindi.identifier);
  assert.equal(selectVoice([hindi], 'hi'), hindi);
  assert.equal(selectVoice([hindi], 'ur-IN'), undefined);
  const h = harness(); await h.controller.read('Urdu text', 'ur-IN');
  assert.deepEqual(h.said, []); assert.equal(h.states.at(-1), 'unavailable');
});
test('stop while voice enumeration is pending prevents late speech', async () => {
  let resolve!: (value: typeof hindi[]) => void;
  let entered!: () => void;
  const enumerating = new Promise<void>(done => { entered = done; });
  const h = harness({ getAvailableVoicesAsync: () => { entered(); return new Promise(done => { resolve = done; }); } });
  const reading = h.controller.read('old alert', 'hi-IN');
  await enumerating; await h.controller.stop(); resolve([hindi]); await reading;
  assert.deepEqual(h.said, []); assert.equal(h.states.at(-1), 'idle');
});
test('superseding alert wins when an older voice lookup returns late', async () => {
  let firstResolve!: (value: typeof hindi[]) => void; let firstEntered!: () => void; let count = 0;
  const firstStarted = new Promise<void>(done => { firstEntered = done; });
  const h = harness({ getAvailableVoicesAsync: () => { if (++count === 1) { firstEntered(); return new Promise(done => { firstResolve = done; }); } return Promise.resolve([hindi]); } });
  const old = h.controller.read('superseded', 'hi-IN'); await firstStarted;
  await h.controller.read('replacement', 'hi-IN'); firstResolve([hindi]); await old;
  assert.deepEqual(h.said, ['replacement']);
});
test('expired alerts are not spoken; playing alerts are stopped on expiry', async () => {
  const h = harness(); await h.controller.read('expired', 'hi-IN', Date.now() - 1);
  assert.deepEqual(h.said, []);
  await h.controller.read('temporary', 'hi-IN', Date.now() + 20);
  await new Promise(done => setTimeout(done, 45));
  assert.deepEqual(h.said, ['temporary']); assert.equal(h.states.at(-1), 'idle'); assert.ok(h.stopCount() >= 3);
});
test('engine failures leave a readable error state', async () => {
  const h = harness({ getAvailableVoicesAsync: async () => { throw new Error('unavailable'); } });
  await h.controller.read('message', 'hi-IN'); assert.equal(h.states.at(-1), 'error');
});
test('a voice provider that never settles exits loading within a bounded deadline', async () => {
  const states: SpeechState[] = []; const said: string[] = [];
  const controller = createSpeechController({ stop: async () => undefined, getAvailableVoicesAsync: () => new Promise(() => {}), speak: text => { said.push(text); } }, state => states.push(state), { voiceTimeoutMs: 15 });
  await controller.read('message', 'hi-IN');
  assert.equal(states.at(-1), 'error');
  assert.deepEqual(said, []);
  await controller.stop();
  assert.equal(states.at(-1), 'idle');
});
