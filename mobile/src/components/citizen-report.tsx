import * as SMS from 'expo-sms';
import { useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { AppState, Keyboard, StyleSheet, TextInput, View } from 'react-native';
import { type CopyKey } from '../../../shared/translations';
import { createReportController, prepareCitizenReport, REPORT_LIMITS, type ReportPhase } from '../lib/citizen-report';
import { usePreferences } from '../state/preferences';
import { Button, Card, Copy, colors, styles } from './ui';

const statusKeys: Partial<Record<ReportPhase, CopyKey>> = {
  invalid: 'reportRequired', checking: 'reportChecking', composing: 'reportComposing', unavailable: 'reportUnavailable',
  cancelled: 'reportCancelled', unknown: 'reportUnknown', accepted: 'reportAccepted', error: 'reportFailed',
};

export function CitizenReport() {
  const { copy, language, rtl } = usePreferences();
  const [manualPlace, setPlace] = useState('');
  const [note, setNote] = useState('');
  const [phase, setPhase] = useState<ReportPhase>('idle');
  const controller = useMemo(() => createReportController(SMS, setPhase), []);
  useEffect(() => {
    controller.setListener(setPhase);
    const subscription = AppState.addEventListener('change', next => { if (next !== 'active') controller.cancelPending(); });
    return () => { controller.setListener(undefined); controller.cancelPending(); subscription.remove(); };
  }, [controller]);
  useFocusEffect(useCallback(() => () => controller.cancelPending(), [controller]));
  useEffect(() => () => controller.cancelPending(), [controller, language]);
  const body = prepareCitizenReport({ manualPlace, note }, language);
  const busy = phase === 'checking' || phase === 'composing';
  const statusKey = statusKeys[phase];
  const direction = rtl ? { writingDirection: 'rtl' as const, textAlign: 'right' as const } : undefined;

  return <Card>
    <Copy accessibilityRole="header" style={styles.heading}>{copy('reportTitle')}</Copy>
    <Copy style={styles.small}>{copy('reportPurpose')}</Copy>
    <View style={{ gap: 7 }}>
      <Copy style={local.label}>{copy('reportPlace')}</Copy>
      <TextInput accessibilityLabel={copy('reportPlace')} placeholder={copy('reportPlaceHint')} placeholderTextColor={colors.muted} value={manualPlace} onChangeText={value => { setPlace(value); setPhase('idle'); }} maxLength={REPORT_LIMITS.place} editable={!busy} style={[local.input, direction]} />
    </View>
    <View style={{ gap: 7 }}>
      <Copy style={local.label}>{copy('reportNote')}</Copy>
      <TextInput accessibilityLabel={copy('reportNote')} placeholder={copy('reportNoteHint')} placeholderTextColor={colors.muted} value={note} onChangeText={value => { setNote(value); setPhase('idle'); }} maxLength={REPORT_LIMITS.note} editable={!busy} multiline textAlignVertical="top" style={[local.input, local.note, direction]} />
      <Copy style={styles.small}>{`${note.length} / ${REPORT_LIMITS.note}`}</Copy>
    </View>
    <View style={local.preview}>
      <Copy style={styles.eyebrow}>{copy('preview')}</Copy>
      <Copy selectable>{body ?? copy('reportRequired')}</Copy>
    </View>
    <Copy style={styles.small}>{copy('reportComposerInfo')}</Copy>
    <Button label={copy('reportOpenSms')} disabled={!body || busy} onPress={() => { Keyboard.dismiss(); void controller.open({ manualPlace, note }, language); }} />
    {statusKey && <Copy accessibilityLiveRegion="polite" style={styles.small}>{copy(statusKey)}</Copy>}
  </Card>;
}

const local = StyleSheet.create({
  label: { fontWeight: '600' },
  input: { backgroundColor: colors.paper, color: colors.ink, borderColor: colors.line, borderWidth: 1, borderRadius: 12, minHeight: 50, padding: 13, fontSize: 15, lineHeight: 23 },
  note: { minHeight: 115 },
  preview: { backgroundColor: '#EAF1EE', padding: 15, borderRadius: 14, gap: 9 },
});
