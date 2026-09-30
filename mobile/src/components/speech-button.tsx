import { View } from 'react-native';
import { useSpeech } from '../hooks/use-speech';
import { usePreferences } from '../state/preferences';
import { Button, Copy, styles } from './ui';

export function SpeechButton({ id, text, expiresAt }: { id: string; text: string; expiresAt?: number }) {
  const { copy } = usePreferences();
  const speech = useSpeech(id, text, expiresAt);
  const busy = speech.state === 'speaking' || speech.state === 'loading';
  return <View style={{ gap: 8 }}>
    <Button label={copy(busy ? 'stop' : 'listen')} icon={busy ? 'stop' : 'speaker'} onPress={() => { if (busy) void speech.stop(); else void speech.read(); }} />
    <Copy accessibilityLiveRegion="polite" style={styles.small}>{speech.state === 'unavailable' ? copy('voiceUnavailable') : speech.state === 'error' ? copy('voiceFailed') : speech.state === 'loading' ? copy('loading') : `${copy('speechReady')}${speech.voiceName ? ` · ${speech.voiceName}` : ''}`}</Copy>
  </View>;
}
