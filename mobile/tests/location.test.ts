import test from 'node:test';
import assert from 'node:assert/strict';
import { createForegroundLocationController, validateFix, FIX_MAX_AGE_MS, type LocationEngine, type LocationReading, type LocationSnapshot } from '../src/lib/foreground-location.ts';

const time = 1_800_000_000_000;
const reading = (changes: Partial<LocationReading> = {}): LocationReading => ({ coords: { latitude: 51.5074, longitude: -0.1278, accuracy: 40 }, timestamp: time, ...changes });
function fixture(overrides: Partial<LocationEngine> = {}, deadlines: { permissionTimeoutMs?: number; fixTimeoutMs?: number } = {}) {
  const states: LocationSnapshot[] = []; let permissions = 0; let watches = 0; let removed = 0;
  let receive: (value: LocationReading) => void = () => {};
  const engine: LocationEngine = {
    requestPermission: async () => { permissions++; return { granted: true }; },
    hasServices: async () => true,
    watch: async callback => { watches++; receive = callback; return { remove: () => { removed++; } }; },
    ...overrides,
  };
  const controller = createForegroundLocationController(engine, state => states.push(state), { now: () => time, ...deadlines });
  return { controller, states, counts: () => ({ permissions, watches, removed }), receive: (value: LocationReading) => receive(value) };
}
test('constructing the location flow does not request permission or start a sensor', () => {
  const f = fixture(); assert.deepEqual(f.counts(), { permissions: 0, watches: 0, removed: 0 });
});
test('denied permission preserves a manual fallback and never starts location', async () => {
  const f = fixture({ requestPermission: async () => ({ granted: false }) });
  await f.controller.request(); assert.equal(f.states.at(-1)?.phase, 'denied'); assert.equal(f.counts().watches, 0); assert.equal(f.states.at(-1)?.fix, undefined);
});
test('cancelling the OS permission wait prevents a later grant from starting location', async () => {
  let grant!: (value: { granted: boolean }) => void;
  const f = fixture({ requestPermission: () => new Promise(done => { grant = done; }) });
  const pending = f.controller.request(); f.controller.cancel(); grant({ granted: true }); await pending;
  assert.equal(f.states.at(-1)?.phase, 'cancelled'); assert.equal(f.counts().watches, 0);
});
test('a fresh foreign coordinate remains exact and its one-fix subscription is removed', async t => {
  const f = fixture(); t.after(() => f.controller.cancel(false));
  await f.controller.request(); f.receive(reading());
  assert.deepEqual(f.states.at(-1)?.fix, { lat: 51.5074, lon: -0.1278, accuracy: 40, timestamp: time });
  assert.equal(f.states.at(-1)?.phase, 'ready'); assert.equal(f.counts().removed, 1);
  f.receive(reading({ coords: { latitude: 25, longitude: 85, accuracy: 10 } }));
  assert.equal(f.states.at(-1)?.fix?.lat, 51.5074);
});
test('invalid, stale, future and imprecise fixes are rejected', () => {
  assert.equal(validateFix(reading({ timestamp: time - FIX_MAX_AGE_MS - 1 }), time), 'stale');
  assert.equal(validateFix(reading({ timestamp: time + 10001 }), time), 'stale');
  assert.equal(validateFix(reading({ coords: { latitude: 91, longitude: 85, accuracy: 10 } }), time), 'unavailable');
  assert.equal(validateFix(reading({ coords: { latitude: 25, longitude: 85, accuracy: null } }), time), 'inaccurate');
  assert.equal(validateFix(reading({ coords: { latitude: 25, longitude: 85, accuracy: 5001 } }), time), 'inaccurate');
});
test('a stale cached update can be replaced by a fresh fix while the request is pending', async t => {
  const f = fixture(); t.after(() => f.controller.cancel(false));
  await f.controller.request(); f.receive(reading({ timestamp: time - FIX_MAX_AGE_MS - 1 }));
  assert.equal(f.states.at(-1)?.phase, 'finding'); assert.equal(f.states.at(-1)?.fix, undefined);
  f.receive(reading()); assert.equal(f.states.at(-1)?.phase, 'ready');
});
test('a request receiving only stale fixes reaches a bounded stale fallback', async () => {
  const f = fixture({}, { fixTimeoutMs: 15 });
  await f.controller.request(); f.receive(reading({ timestamp: time - FIX_MAX_AGE_MS - 1 }));
  await new Promise(done => setTimeout(done, 35));
  assert.equal(f.states.at(-1)?.phase, 'stale'); assert.equal(f.states.at(-1)?.fix, undefined); assert.equal(f.counts().removed, 1);
});
test('late subscription setup is removed after cancellation and cannot apply a fix', async () => {
  let ready!: () => void; const starting = new Promise<void>(done => { ready = done; });
  let registered!: (value: { remove: () => void }) => void; let receive!: (value: LocationReading) => void; let removed = 0;
  const f = fixture({ watch: callback => { receive = callback; ready(); return new Promise(done => { registered = done; }); } });
  const pending = f.controller.request(); await starting; f.controller.cancel();
  receive(reading()); registered({ remove: () => { removed++; } }); await pending;
  assert.equal(removed, 1); assert.equal(f.states.at(-1)?.phase, 'cancelled'); assert.equal(f.states.at(-1)?.fix, undefined);
});
test('disabled services and a stalled permission request produce readable fallback', async () => {
  const off = fixture({ hasServices: async () => false }); await off.controller.request();
  assert.equal(off.states.at(-1)?.phase, 'unavailable'); assert.equal(off.counts().watches, 0);
  const stalled = fixture({ requestPermission: () => new Promise(() => {}) }, { permissionTimeoutMs: 15 });
  void stalled.controller.request(); await new Promise(done => setTimeout(done, 35));
  assert.equal(stalled.states.at(-1)?.phase, 'unavailable');
});
test('clearing a device fix discards coordinates while preserving permission state', async () => {
  const f = fixture(); await f.controller.request(); f.receive(reading()); f.controller.reset();
  assert.deepEqual(f.states.at(-1), { phase: 'idle', permission: 'granted' });
});
