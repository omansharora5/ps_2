export type DeviceFix = { lat: number; lon: number; accuracy: number; timestamp: number };
export type LocationReading = { coords: { latitude: number; longitude: number; accuracy: number | null }; timestamp: number };
export type LocationPhase = 'idle' | 'requesting' | 'finding' | 'ready' | 'denied' | 'unavailable' | 'cancelled' | 'stale' | 'inaccurate';
export type LocationSnapshot = { phase: LocationPhase; permission: 'unknown' | 'granted' | 'denied'; fix?: DeviceFix };
export type LocationEngine = {
  requestPermission: () => Promise<{ granted: boolean }>;
  hasServices: () => Promise<boolean>;
  watch: (success: (reading: LocationReading) => void, error: () => void) => Promise<{ remove: () => void }>;
};
export const FIX_MAX_AGE_MS = 120000;
export const FIX_MAX_ACCURACY_METRES = 5000;
export function validateFix(reading: LocationReading, now = Date.now()): DeviceFix | 'stale' | 'inaccurate' | 'unavailable' {
  const { latitude: lat, longitude: lon, accuracy } = reading.coords;
  if (!Number.isFinite(lat) || lat < -90 || lat > 90 || !Number.isFinite(lon) || lon < -180 || lon > 180 || !Number.isFinite(reading.timestamp)) return 'unavailable';
  if (now - reading.timestamp > FIX_MAX_AGE_MS || reading.timestamp > now + 10000) return 'stale';
  if (accuracy === null || !Number.isFinite(accuracy) || accuracy < 0 || accuracy > FIX_MAX_ACCURACY_METRES) return 'inaccurate';
  return { lat, lon, accuracy, timestamp: reading.timestamp };
}

/** A cancellable, one-fix foreground subscription. Coordinates never leave this module's caller. */
export function createForegroundLocationController(engine: LocationEngine, notify: (state: LocationSnapshot) => void, options: { permissionTimeoutMs?: number; fixTimeoutMs?: number; now?: () => number } = {}) {
  let generation = 0;
  let subscription: { remove: () => void } | undefined;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let permission: LocationSnapshot['permission'] = 'unknown';
  const now = options.now ?? Date.now;
  const cleanup = () => {
    if (timer) clearTimeout(timer); timer = undefined;
    subscription?.remove(); subscription = undefined;
  };
  const cancel = (announce = true) => {
    generation++; cleanup();
    if (announce) notify({ phase: 'cancelled', permission });
  };
  return {
    cancel,
    reset() { cancel(false); notify({ phase: 'idle', permission }); },
    async request() {
      cancel(false);
      const token = generation;
      let settled = false;
      let lastFailure: 'stale' | 'inaccurate' | 'unavailable' = 'unavailable';
      const current = () => token === generation && !settled;
      const finish = (phase: LocationPhase, fix?: DeviceFix) => {
        if (!current()) return;
        settled = true; cleanup(); notify({ phase, permission, ...(fix ? { fix } : {}) });
        if (fix) timer = setTimeout(() => { if (token === generation) notify({ phase: 'stale', permission, fix }); }, Math.max(1, FIX_MAX_AGE_MS - (now() - fix.timestamp)));
      };
      notify({ phase: 'requesting', permission });
      timer = setTimeout(() => finish('unavailable'), options.permissionTimeoutMs ?? 45000);
      try {
        const result = await engine.requestPermission();
        if (!current()) return;
        permission = result.granted ? 'granted' : 'denied';
        if (!result.granted) { finish('denied'); return; }
        if (timer) clearTimeout(timer);
        timer = setTimeout(() => finish(lastFailure), options.fixTimeoutMs ?? 15000);
        notify({ phase: 'finding', permission });
        if (!await engine.hasServices()) { finish('unavailable'); return; }
        if (!current()) return;
        const handle = await engine.watch(reading => {
          if (!current()) return;
          const fix = validateFix(reading, now());
          if (typeof fix === 'string') { lastFailure = fix; return; }
          finish('ready', fix);
        }, () => finish('unavailable'));
        // The first callback or cancellation can occur before subscription setup resolves.
        if (!current()) handle.remove(); else subscription = handle;
      } catch { finish('unavailable'); }
    },
  };
}
