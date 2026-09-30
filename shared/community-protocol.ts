export type Answer = 'yes' | 'no' | 'unsure';
export type CommunityReport = Readonly<{ request_id: string; installation_id: string; cell_id: string; answer: Answer; observed_at_utc: string; consent_training: boolean }>;
export type Aggregate = { public_status: string; counts_withheld: true; independent_people_verified: false; automatic_training: false };
export type CommunityState = {
  enabled: boolean; cells: { id: string; name: string; bbox: number[] }[]; selected_cell: string;
  prompt: { question: string; forecast_status: string; window_start_utc: string; window_end_utc: string };
  aggregate: Aggregate; evidence_card: Record<string, unknown>; scorecard: Record<string, unknown>; benchmark: Record<string, unknown>;
};
export type Receipt = { report_id: string; status: 'recorded_unverified'; duplicate: boolean; aggregate: Aggregate };
export type SavedReport = { request: CommunityReport; receipt: Receipt | null };
export const INSTALLATION_KEY = 'vajra.community.installation.v1';
export const REPORT_KEY = 'vajra.community.report.v1';
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const object = (value: unknown): Record<string, unknown> => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Invalid community object');
  return value as Record<string, unknown>;
};
const text = (value: unknown): string => {
  if (typeof value !== 'string' || !value.length || value.length > 4000) throw new Error('Invalid community text');
  return value;
};
const flag = (value: unknown): boolean => { if (typeof value !== 'boolean') throw new Error('Invalid community flag'); return value; };
function instant(value: unknown): string {
  const result = text(value);
  if (!/^\d{4}-\d{2}-\d{2}T.+(?:Z|[+-]\d{2}:\d{2})$/.test(result) || !Number.isFinite(Date.parse(result))) throw new Error('Invalid report time');
  return result;
}
export function parseAggregate(value: unknown): Aggregate {
  const a = object(value);
  if (a.counts_withheld !== true || a.independent_people_verified !== false || a.automatic_training !== false) throw new Error('Unexpected public evidence policy');
  return { public_status: text(a.public_status), counts_withheld: true, independent_people_verified: false, automatic_training: false };
}
export function parseCommunityState(value: unknown): CommunityState {
  const s = object(value), p = object(s.prompt);
  if (!Array.isArray(s.cells) || !s.cells.length || s.cells.length > 100) throw new Error('Invalid pilot cells');
  const cells = s.cells.map(value => {
    const c = object(value);
    if (!Array.isArray(c.bbox) || c.bbox.length !== 4 || !c.bbox.every(v => typeof v === 'number' && Number.isFinite(v))) throw new Error('Invalid cell bounds');
    return { id: text(c.id), name: text(c.name), bbox: c.bbox as number[] };
  });
  const selected = text(s.selected_cell);
  if (!cells.some(c => c.id === selected) || new Set(cells.map(c => c.id)).size !== cells.length) throw new Error('Invalid cell selection');
  return { enabled: flag(s.enabled), cells, selected_cell: selected, prompt: { question: text(p.question), forecast_status: text(p.forecast_status), window_start_utc: instant(p.window_start_utc), window_end_utc: instant(p.window_end_utc) }, aggregate: parseAggregate(s.aggregate), evidence_card: object(s.evidence_card), scorecard: object(s.scorecard), benchmark: object(s.benchmark) };
}
export function parseReceipt(value: unknown): Receipt {
  const r = object(value);
  if (r.status !== 'recorded_unverified') throw new Error('Unexpected report status');
  return { report_id: text(r.report_id), status: 'recorded_unverified', duplicate: flag(r.duplicate), aggregate: parseAggregate(r.aggregate) };
}
export function parseReport(value: unknown): CommunityReport {
  const r = object(value);
  if (typeof r.request_id !== 'string' || !UUID.test(r.request_id) || typeof r.installation_id !== 'string' || !UUID.test(r.installation_id) || !['yes', 'no', 'unsure'].includes(String(r.answer))) throw new Error('Invalid report identity or answer');
  return Object.freeze({ request_id: r.request_id, installation_id: r.installation_id, cell_id: text(r.cell_id), answer: r.answer as Answer, observed_at_utc: instant(r.observed_at_utc), consent_training: flag(r.consent_training) });
}
export function parseSavedReport(raw: string | null): SavedReport | null {
  if (raw === null) return null;
  const saved = object(JSON.parse(raw));
  return { request: parseReport(saved.request), receipt: saved.receipt === null ? null : parseReceipt(saved.receipt) };
}
// Random identifiers deduplicate retries. They are not authentication credentials.
export function reportUUID(): string {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, char => {
    const n = Math.floor(Math.random() * 16);
    return (char === 'x' ? n : (n & 3) | 8).toString(16);
  });
}
export function installationId(stored: string | null): string {
  if (stored !== null && !UUID.test(stored)) throw new Error('Invalid saved installation identity');
  return stored ?? reportUUID();
}
export async function communityRequest(base: string, path: string, body?: unknown, signal?: AbortSignal): Promise<unknown> {
  if (base && !/^https?:\/\//i.test(base)) throw new Error('Invalid research API URL');
  const controller = new AbortController(), abort = () => controller.abort();
  signal?.addEventListener('abort', abort, { once: true });
  if (signal?.aborted) abort();
  const timeout = setTimeout(abort, 15000);
  try {
    const response = await fetch(`${base.replace(/\/$/, '')}/api/community/${path}`, { signal: controller.signal, ...(body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }) });
    if (!response.ok) {
      const error = await response.json().catch(() => null);
      throw new Error(typeof error?.detail === 'string' ? error.detail : `Request rejected (${response.status})`);
    }
    return await response.json();
  } finally { clearTimeout(timeout); signal?.removeEventListener('abort', abort); }
}
