import { t, type LanguageCode } from '../../../shared/translations.ts';

export const REPORT_LIMITS = { place: 100, note: 500 } as const;
export type CitizenDraft = { manualPlace: string; note: string };
export type ReportPhase = 'idle' | 'invalid' | 'checking' | 'composing' | 'unavailable' | 'cancelled' | 'unknown' | 'accepted' | 'error';
export type SmsComposer = {
  isAvailableAsync: () => Promise<boolean>;
  sendSMSAsync: (recipients: string[], body: string) => Promise<{ result: string }>;
};

/** Only user-entered fields belong in this message; location and practice alerts are never inputs. */
export function prepareCitizenReport(draft: CitizenDraft, language: LanguageCode): string | null {
  const place = draft.manualPlace.trim();
  const note = draft.note.trim();
  if (!place || !note || place.length > REPORT_LIMITS.place || note.length > REPORT_LIMITS.note) return null;
  return [t(language, 'reportUnverified'), `${t(language, 'reportPlace')}: ${place}`, `${t(language, 'reportNote')}: ${note}`, t(language, 'reportNotOfficial')].join('\n\n');
}

export function createReportController(engine: SmsComposer, notify: (phase: ReportPhase) => void, options: { availabilityTimeoutMs?: number } = {}) {
  let phase: ReportPhase = 'idle';
  let listener: ((phase: ReportPhase) => void) | undefined = notify;
  let generation = 0;
  let deadline: ReturnType<typeof setTimeout> | undefined;
  const publish = (next: ReportPhase) => { phase = next; listener?.(next); };
  const clearDeadline = () => { if (deadline) clearTimeout(deadline); deadline = undefined; };
  const cancelPending = () => {
    if (phase !== 'checking') return;
    generation++;
    clearDeadline();
    publish('idle');
  };
  return {
    cancelPending,
    setListener(next: ((phase: ReportPhase) => void) | undefined) { listener = next; },
    async open(draft: CitizenDraft, language: LanguageCode) {
      if (phase === 'checking' || phase === 'composing') return;
      const body = prepareCitizenReport(draft, language);
      if (!body) { publish('invalid'); return; }
      const token = ++generation;
      publish('checking');
      try {
        const available = await Promise.race([
          engine.isAvailableAsync(),
          new Promise<never>((_, reject) => { deadline = setTimeout(() => reject(new Error('SMS availability deadline')), options.availabilityTimeoutMs ?? 3000); }),
        ]);
        if (token !== generation) return;
        clearDeadline();
        if (!available) { publish('unavailable'); return; }
        publish('composing');
        // Recipient choice and the final send action remain in the OS messaging application.
        const response = await engine.sendSMSAsync([], body);
        if (token === generation) publish(response.result === 'cancelled' ? 'cancelled' : response.result === 'sent' ? 'accepted' : 'unknown');
      } catch {
        if (token === generation) publish('error');
      } finally {
        if (token === generation) clearDeadline();
      }
    },
  };
}
