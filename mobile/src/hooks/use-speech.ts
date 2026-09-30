import { useCallback, useEffect, useMemo, useState } from 'react';
import { AppState } from 'react-native';
import { useFocusEffect } from 'expo-router';
import * as Speech from 'expo-speech';
import { createSpeechController, type SpeechState } from '../lib/speech-controller';
import { usePreferences } from '../state/preferences';

export function useSpeech(messageId: string, text: string, expiresAt?: number) {
  const { locale } = usePreferences();
  const [state, setState] = useState<SpeechState>('idle');
  const [voiceName, setVoice] = useState('');
  const controller = useMemo(() => createSpeechController(Speech, (next, voice) => { setState(next); setVoice(voice ?? ''); }), []);
  useEffect(() => { void controller.stop(); return () => { void controller.stop(); }; }, [controller, messageId, locale, text, expiresAt]);
  useFocusEffect(useCallback(() => () => { void controller.stop(); }, [controller]));
  useEffect(() => {
    const subscription = AppState.addEventListener('change', state => { if (state !== 'active') void controller.stop(); });
    return () => subscription.remove();
  }, [controller]);
  return { state, voiceName, read: () => controller.read(text, locale, expiresAt), stop: controller.stop };
}
