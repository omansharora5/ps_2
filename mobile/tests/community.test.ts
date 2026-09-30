import { test } from 'node:test';
import assert from 'node:assert/strict';
import { communityRequest, installationId, parseAggregate, parseCommunityState, parseReport, parseSavedReport, reportUUID } from '../../shared/community-protocol.ts';
import { COMMUNITY_COPY_KEYS, communityDictionaries } from '../../shared/community-translations.ts';

const id = '128b1f21-1a30-4fbb-83c2-bcf36c39c0dc';
const aggregate = { public_status: 'collecting', counts_withheld: true, independent_people_verified: false, automatic_training: false };
const report = () => ({ request_id: id, installation_id: id, cell_id: 'delhi-central', answer: 'yes', observed_at_utc: '2026-09-30T12:00:00Z', consent_training: false });
const state = () => ({ enabled: false, cells: [{ id: 'delhi-central', name: 'Central Delhi pilot cell', bbox: [77, 28, 78, 29] }], selected_cell: 'delhi-central', prompt: { question: 'Rain?', forecast_status: 'unavailable', window_start_utc: '2026-09-30T12:00:00Z', window_end_utc: '2026-09-30T12:15:00Z' }, aggregate, evidence_card: { status: 'unavailable' }, scorecard: { status: 'unavailable' }, benchmark: { status: 'metadata_only' } });

test('public boundary preserves withheld counts and refuses automatic-training claims', () => {
  assert.deepEqual(parseCommunityState(state()).aggregate, aggregate);
  assert.throws(() => parseAggregate({ ...aggregate, automatic_training: true }));
  assert.throws(() => parseAggregate({ ...aggregate, counts_withheld: false }));
  assert.equal('yes' in parseAggregate({ ...aggregate, yes: 8, revision: 'private' }), false);
  assert.throws(() => parseCommunityState({ ...state(), selected_cell: 'unknown' }));
});

test('saved request restoration preserves the original timestamp, identity, answer and consent', () => {
  const frozen = parseReport(report());
  assert.equal(Object.isFrozen(frozen), true);
  const saved = parseSavedReport(JSON.stringify({ request: frozen, receipt: null }));
  assert.deepEqual(saved?.request, frozen);
  assert.equal(saved?.request.consent_training, false);
  assert.equal(parseSavedReport(null), null);
  assert.throws(() => parseReport({ ...report(), observed_at_utc: '2026-09-30T12:00:00' }));
  assert.throws(() => parseReport({ ...report(), answer: 'probably' }));
  assert.throws(() => parseSavedReport('{broken'));
  const receipt = { report_id: 'record-1', status: 'recorded_unverified', duplicate: true, aggregate };
  assert.equal(parseSavedReport(JSON.stringify({ request: report(), receipt }))?.receipt?.duplicate, true);
});

test('installation identity remains stable and malformed storage cannot silently generate a fresh identity', () => {
  assert.equal(installationId(id), id);
  assert.match(installationId(null), /^[a-f\d-]{36}$/i);
  assert.notEqual(reportUUID(), reportUUID());
  assert.throws(() => installationId('bad-id'));
});

test('HTTP retry sends identical stored payload and exposes API rejections', async () => {
  const original = globalThis.fetch; const sent: string[] = [];
  globalThis.fetch = async (_input, init) => {
    sent.push(String(init?.body));
    return sent.length === 1 ? new Response(JSON.stringify({ detail: 'Connection interrupted' }), { status: 503 }) : new Response(JSON.stringify({ recorded: true }), { status: 200 });
  };
  try {
    const payload = parseReport(report());
    await assert.rejects(communityRequest('https://example.org', 'reports', payload), /Connection interrupted/);
    await communityRequest('https://example.org', 'reports', payload);
    assert.equal(sent[0], sent[1]);
    assert.equal(JSON.parse(sent[1]).observed_at_utc, report().observed_at_utc);
  } finally { globalThis.fetch = original; }
});

test('new reporting copy covers English plus all twelve Indian languages', () => {
  assert.equal(Object.keys(communityDictionaries).length, 13);
  for (const dictionary of Object.values(communityDictionaries)) for (const key of COMMUNITY_COPY_KEYS) assert.ok(dictionary[key]?.trim(), key);
  assert.match(communityDictionaries.hi.communityQuestion, /बारिश/);
  assert.match(communityDictionaries.ur.communityQuestion, /بارش/);
});
