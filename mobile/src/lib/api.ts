export type Catalog = {
  schema_version: number; training_ready: boolean; scope: string;
  collections: { id: string; name: string; status: string; local_file_count: number; bytes: number }[];
  sources: { id: string; name: string; provider: string; source_url: string; status: string; local_file_count: number }[];
};
export type Simulation = {
  id: string; mode: 'simulation'; status: string; label: string;
  target: string; issued_at: string; valid_at: string; time_note: string; horizon: number;
  sites: { id: string; name: string; probability: number | null }[];
};
const object = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null;
export function parseCatalog(value: unknown): Catalog {
  if (!object(value) || value.schema_version !== 1 || typeof value.training_ready !== 'boolean' || typeof value.scope !== 'string' || !Array.isArray(value.collections) || !Array.isArray(value.sources)) throw new Error('Invalid catalogue');
  for (const item of value.collections) {
    if (!object(item) || typeof item.id !== 'string' || typeof item.name !== 'string' || typeof item.status !== 'string' || typeof item.local_file_count !== 'number' || typeof item.bytes !== 'number') throw new Error('Invalid collection');
  }
  for (const item of value.sources) {
    if (!object(item) || typeof item.id !== 'string' || typeof item.name !== 'string' || typeof item.provider !== 'string' || typeof item.source_url !== 'string' || typeof item.status !== 'string' || typeof item.local_file_count !== 'number') throw new Error('Invalid source');
  }
  return value as Catalog;
}
export function parseSimulation(value: unknown): Simulation {
  if (!object(value) || value.mode !== 'simulation' || typeof value.id !== 'string' || typeof value.status !== 'string' || typeof value.label !== 'string' || typeof value.target !== 'string' || typeof value.issued_at !== 'string' || !Number.isFinite(Date.parse(value.issued_at)) || typeof value.valid_at !== 'string' || !Number.isFinite(Date.parse(value.valid_at)) || typeof value.time_note !== 'string' || typeof value.horizon !== 'number' || !Number.isFinite(value.horizon) || value.horizon < 0 || !Array.isArray(value.sites)) throw new Error('Invalid simulation');
  for (const item of value.sites) {
    if (!object(item) || typeof item.id !== 'string' || typeof item.name !== 'string' || !(item.probability === null || (typeof item.probability === 'number' && Number.isFinite(item.probability) && item.probability >= 0 && item.probability <= 1))) throw new Error('Invalid probability');
  }
  return value as Simulation;
}
export function safeExternalUrl(value: string): boolean {
  try { return new URL(value).protocol === 'https:'; } catch { return false; }
}
export const apiBase = (process.env.EXPO_PUBLIC_API_URL ?? '').trim().replace(/\/$/, '');
export async function requestApi(path: '/api/data/catalog' | '/api/runs' | '/api/operations/state', signal: AbortSignal) {
  if (!/^https?:\/\//i.test(apiBase)) throw new Error('API URL missing');
  const timeout = new AbortController();
  const abort = () => timeout.abort();
  signal.addEventListener('abort', abort, { once: true });
  if (signal.aborted) timeout.abort();
  const timer = setTimeout(abort, 15000);
  try {
    const response = await fetch(`${apiBase}${path}`, {
      signal: timeout.signal,
      ...(path === '/api/runs' ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ mode: 'simulation', seed: 62, step: 8, horizon: 30, hazard: 'lightning', disabled: [], stale: [] }) } : {}),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json() as unknown;
  } finally { clearTimeout(timer); signal.removeEventListener('abort', abort); }
}
