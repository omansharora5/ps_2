export type DeviceVoice = { identifier: string; language: string; name: string };
export type SpeechState = 'idle' | 'loading' | 'speaking' | 'unavailable' | 'error';
export type SpeechEngine = {
  stop: () => Promise<void>;
  getAvailableVoicesAsync: () => Promise<DeviceVoice[]>;
  speak: (text: string, options: {
    language: string; voice: string; rate: number;
    onStart: () => void; onDone: () => void; onStopped: () => void; onError: (error: unknown) => void;
  }) => void;
};

export function selectVoice(voices: DeviceVoice[], locale: string): DeviceVoice | undefined {
  const normalized = locale.toLowerCase().replaceAll('_', '-');
  return voices.find(v => v.language.toLowerCase().replaceAll('_', '-') === normalized)
    ?? voices.find(v => v.language.toLowerCase().split(/[-_]/)[0] === normalized.split('-')[0]);
}

/** Serializing stop operations prevents a cancelled request from stopping newer audio. */
export function createSpeechController(engine: SpeechEngine, notify: (state: SpeechState, voice?: string) => void, options: { voiceTimeoutMs?: number } = {}) {
  let generation = 0;
  let stopQueue = Promise.resolve();
  let expiryTimer: ReturnType<typeof setTimeout> | undefined;
  const clearExpiry = () => { if (expiryTimer) clearTimeout(expiryTimer); expiryTimer = undefined; };
  const queueStop = () => {
    stopQueue = stopQueue.catch(() => undefined).then(() => engine.stop());
    return stopQueue;
  };
  const stop = async () => {
    const token = ++generation;
    clearExpiry();
    notify('idle');
    try { await queueStop(); } catch { if (token === generation) notify('error'); }
  };
  return {
    stop,
    async read(text: string, locale: string, expiresAt?: number) {
      const token = ++generation;
      clearExpiry();
      notify('loading');
      const current = () => token === generation;
      const eligible = () => expiresAt === undefined || Date.now() < expiresAt;
      try {
        await queueStop();
        if (!current()) return;
        if (!eligible()) { notify('idle'); return; }
        let voiceTimer: ReturnType<typeof setTimeout> | undefined;
        let voices: DeviceVoice[];
        try {
          voices = await Promise.race([
            engine.getAvailableVoicesAsync(),
            new Promise<never>((_, reject) => { voiceTimer = setTimeout(() => reject(new Error('Voice lookup timed out')), options.voiceTimeoutMs ?? 3000); }),
          ]);
        } finally { if (voiceTimer) clearTimeout(voiceTimer); }
        const voice = selectVoice(voices, locale);
        if (!current()) return;
        if (!eligible()) { notify('idle'); return; }
        if (!voice) { notify('unavailable'); return; }
        const end = () => { if (current()) { clearExpiry(); notify('idle'); } };
        engine.speak(text, {
          language: locale, voice: voice.identifier, rate: 0.9,
          onStart: () => { if (current()) notify('speaking', voice.name); },
          onDone: end, onStopped: end,
          onError: () => { if (current()) { clearExpiry(); notify('error'); } },
        });
        if (expiresAt !== undefined) expiryTimer = setTimeout(() => { if (current()) void stop(); }, Math.max(0, expiresAt - Date.now()));
      } catch { if (current()) notify('error'); }
    },
  };
}
