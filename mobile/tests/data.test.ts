import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { COPY_KEYS, LANGUAGES, dictionaries, t } from '../../shared/translations.ts';
import { interpolateFocus, projectPoint } from '../../shared/earth-math.ts';
import { parseCatalog, parseSimulation, safeExternalUrl } from '../src/lib/api.ts';

test('all 13 locales are complete UTF-8 and critical copy is translated', () => {
  assert.equal(LANGUAGES.length, 13);
  for (const { code } of LANGUAGES) {
    for (const key of COPY_KEYS) {
      assert.ok(dictionaries[code][key].length > 0, `${code}.${key}`);
      assert.doesNotMatch(dictionaries[code][key], /\uFFFD|\?{2,}/, `${code}.${key}`);
    }
    if (code !== 'en') for (const key of ['practiceBody', 'simulationBody', 'voiceUnavailable', 'currentUnavailable', 'useLocation', 'locationDenied', 'liveCoverageUnavailable', 'regionUnknown'] as const) assert.notEqual(dictionaries[code][key], dictionaries.en[key]);
  }
  assert.equal(t('unknown', 'practiceBody'), dictionaries.en.practiceBody);
  assert.equal(LANGUAGES.find(item => item.code === 'ur')?.rtl, true);
});
test('offline city aliases retain native scripts and valid coordinates', () => {
  const places = JSON.parse(readFileSync(new URL('../../shared/locations.json', import.meta.url), 'utf8'));
  assert.equal(places.length, 19);
  for (const place of places) {
    assert.ok(place.lat > 0 && place.lat < 40 && place.lon > 65 && place.lon < 100);
    assert.ok(place.aliases.some((alias: string) => /[^\x00-\x7F]/.test(alias)));
    assert.ok(place.aliases.every((alias: string) => !/[?\uFFFD]/.test(alias)));
  }
  assert.ok(places.find((place: { id: string }) => place.id === 'patna').aliases.includes('पटना'));
});
test('earth focus centers the selected coordinate and crosses dateline by short route', () => {
  const point = projectPoint(25, 85, { lat: 25, lon: 85 });
  assert.ok(Math.abs(point.x) < 1e-9 && Math.abs(point.y) < 1e-9 && point.z > 0.99);
  assert.ok(projectPoint(-25, -95, { lat: 25, lon: 85 }).z < 0);
  assert.equal(interpolateFocus({ lat: 0, lon: 179 }, { lat: 0, lon: -179 }, 0.5).lon, 180);
});
test('API boundary rejects malformed catalogue and observed data disguised as simulation', () => {
  assert.throws(() => parseCatalog({ collections: [], sources: [] }));
  assert.equal(parseCatalog({ schema_version: 1, training_ready: false, scope: 'reference', collections: [], sources: [] }).training_ready, false);
  assert.throws(() => parseSimulation({ id: 'x', mode: 'observed', status: 'available', label: 'x', sites: [] }));
  const simulation = { id: 'x', mode: 'simulation', status: 'simulation', label: 'x', target: 'Simulated flash within 8 km', issued_at: '2020-01-01T00:00:00Z', valid_at: '2020-01-01T00:30:00Z', time_note: 'Synthetic UTC', horizon: 30, sites: [{ id: 'x', name: 'x', probability: 0.5 }] };
  assert.equal(parseSimulation(simulation).sites[0].probability, 0.5);
  assert.throws(() => parseSimulation({ ...simulation, sites: [{ id: 'x', name: 'x', probability: 1.1 }] }));
  assert.throws(() => parseSimulation({ ...simulation, valid_at: 'not-a-timestamp' }));
  assert.equal(safeExternalUrl('javascript:alert(1)'), false);
  assert.equal(safeExternalUrl('https://mausam.imd.gov.in/'), true);
});
