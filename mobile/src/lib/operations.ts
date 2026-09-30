export type CandidateSummary = {
  mode: 'training_candidate'; raw_brier: number; calibrated_brier: number; baseline_brier: number;
  test_event_count: number; recommendation: 'retain_baseline' | 'research_review_only'; promoted: false;
};
export type OperationJob = {
  id: string; kind: 'starter_audit' | 'radar_replay' | 'train_candidate';
  status: 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled'; stage: string; scope: string;
  created_at: string; updated_at: string; error: string | null; summary: CandidateSummary | null;
};
export type Operations = {
  scope: 'research_only';
  worker: { available: boolean; last_seen_at: string | null };
  learning: { enabled: boolean; status: string; note: string; last_checked_at: string | null };
  datasets: { id: string; name: string; scope: string; event_count: number; learning_eligible: boolean; readiness_reasons: string[]; target: string }[];
  jobs: OperationJob[];
};

function record(value: unknown): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) throw new Error('Invalid operations object');
  return value as Record<string, unknown>;
}
function text(value: unknown, maximum = 2000): string {
  if (typeof value !== 'string' || value.length > maximum || value.trim().length === 0) throw new Error('Invalid operations text');
  return value;
}
function boolean(value: unknown): boolean {
  if (typeof value !== 'boolean') throw new Error('Invalid operations flag');
  return value;
}
function count(value: unknown): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) throw new Error('Invalid operations count');
  return value;
}
function score(value: unknown): number {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > 1) throw new Error('Invalid Brier score');
  return value;
}
function timestamp(value: unknown): string {
  const candidate = text(value, 50);
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(candidate) || !Number.isFinite(Date.parse(candidate))) throw new Error('Invalid operations timestamp');
  return candidate;
}
function nullableTimestamp(value: unknown): string | null { return value === null ? null : timestamp(value); }
function list(value: unknown, maximum = 1000): unknown[] {
  if (!Array.isArray(value) || value.length > maximum) throw new Error('Invalid operations list');
  return value;
}
function option<T extends string>(value: unknown, allowed: readonly T[]): T {
  const found = allowed.find(item => item === value);
  if (found === undefined) throw new Error('Invalid operations status');
  return found;
}
function parseSummary(value: unknown): CandidateSummary | null {
  if (value === null || value === undefined) return null;
  const data = record(value);
  if (data.mode !== 'training_candidate') return null;
  if (data.promoted !== false) throw new Error('Unexpected model promotion');
  const eventCount = count(data.test_event_count);
  if (eventCount === 0) throw new Error('Candidate has no test events');
  return {
    mode: 'training_candidate', raw_brier: score(data.raw_brier), calibrated_brier: score(data.calibrated_brier),
    baseline_brier: score(data.baseline_brier), test_event_count: eventCount,
    recommendation: option(data.recommendation, ['retain_baseline', 'research_review_only'] as const), promoted: false,
  };
}

export function parseOperations(value: unknown): Operations {
  const data = record(value);
  if (data.schema_version !== 1 || data.scope !== 'research_only') throw new Error('Unsupported operations scope');
  const worker = record(data.worker), learning = record(data.learning);
  const datasets = list(data.datasets, 100).map(value => {
    const item = record(value);
    return {
      id: text(item.id, 160), name: text(item.name, 300), scope: text(item.scope, 300),
      event_count: count(item.event_count), learning_eligible: boolean(item.learning_eligible),
      readiness_reasons: list(item.readiness_reasons, 30).map(value => text(value)), target: text(item.target),
    };
  });
  const jobs = list(data.jobs).map(value => {
    const item = record(value);
    return {
      id: text(item.id, 160), kind: option(item.kind, ['starter_audit', 'radar_replay', 'train_candidate'] as const),
      status: option(item.status, ['queued', 'running', 'succeeded', 'failed', 'cancelled'] as const),
      stage: text(item.stage, 300), scope: text(item.scope, 300), created_at: timestamp(item.created_at),
      updated_at: timestamp(item.updated_at), error: item.error === null ? null : text(item.error), summary: parseSummary(item.summary),
    };
  });
  for (const items of [datasets, jobs]) if (new Set(items.map(item => item.id)).size !== items.length) throw new Error('Duplicate operations identity');
  return {
    scope: 'research_only', worker: { available: boolean(worker.available), last_seen_at: nullableTimestamp(worker.last_seen_at) },
    learning: { enabled: boolean(learning.enabled), status: text(learning.status, 200), note: text(learning.note), last_checked_at: nullableTimestamp(learning.last_checked_at) },
    datasets, jobs,
  };
}

export function recentJobs(jobs: OperationJob[]): OperationJob[] {
  return [...jobs].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at) || b.id.localeCompare(a.id));
}
export function latestCandidate(jobs: OperationJob[]): OperationJob | undefined {
  return recentJobs(jobs).find(job => job.kind === 'train_candidate' && job.status === 'succeeded' && job.summary !== null);
}
export function utcTime(value: string | number): string { return new Date(value).toISOString().replace('T', ' ').replace(/\.\d{3}Z$/, ' UTC'); }

export type OperationsSnapshot = {
  phase: 'idle' | 'loading' | 'ready' | 'error' | 'stale'; data: Operations | null; receivedAt: number | null;
};
export const EMPTY_OPERATIONS: OperationsSnapshot = { phase: 'idle', data: null, receivedAt: null };

export function createOperationsMonitor(request: (signal: AbortSignal) => Promise<unknown>, changed: (state: OperationsSnapshot) => void, now = Date.now) {
  let state: OperationsSnapshot = EMPTY_OPERATIONS;
  let generation = 0;
  let active: { abort: AbortController; promise: Promise<void> } | null = null;
  const publish = (next: OperationsSnapshot) => { state = next; changed(next); };
  return {
    refresh(): Promise<void> {
      if (active) return active.promise;
      const abort = new AbortController(), token = ++generation;
      publish({ ...state, phase: 'loading' });
      const promise = Promise.resolve().then(async () => {
        if (abort.signal.aborted) return;
        const value = await request(abort.signal);
        if (token !== generation || abort.signal.aborted) return;
        const data = parseOperations(value);
        publish({ phase: 'ready', data, receivedAt: now() });
      }).catch(() => {
        if (token === generation && !abort.signal.aborted) publish({ ...state, phase: state.data ? 'stale' : 'error' });
      }).finally(() => { if (token === generation) active = null; });
      active = { abort, promise };
      return promise;
    },
    pause(): void {
      generation += 1;
      active?.abort.abort();
      active = null;
      publish({ ...state, phase: state.data ? 'stale' : 'idle' });
    },
  };
}
