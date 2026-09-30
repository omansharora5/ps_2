import AsyncStorage from '@react-native-async-storage/async-storage';
import { useEffect, useRef, useState } from 'react';
import { Pressable, View } from 'react-native';
import { Button, Card, Copy, colors, styles } from './ui';
import { usePreferences } from '../state/preferences';
import { requestCommunity } from '../lib/community';
import { installationId, INSTALLATION_KEY, parseCommunityState, parseReceipt, parseReport, parseSavedReport, REPORT_KEY, reportUUID, type Answer, type CommunityState, type SavedReport } from '../../../shared/community-protocol';
import type { CopyKey } from '../../../shared/translations';

const answerKeys: Record<Answer, CopyKey> = { yes: 'communityYes', no: 'communityNo', unsure: 'communityUnsure' };
export function CommunityReport() {
  const { copy } = usePreferences();
  const [cell, setCell] = useState(''), [answer, setAnswer] = useState<Answer | null>(null);
  const [here, setHere] = useState(false), [consent, setConsent] = useState(false);
  const [installation, setInstallation] = useState<string | null>(null), [saved, setSaved] = useState<SavedReport | null>(null);
  const [state, setState] = useState<CommunityState | null>(null), [loading, setLoading] = useState(true);
  const [storageError, setStorageError] = useState(false), [loadError, setLoadError] = useState(false), [error, setError] = useState('');
  const [busy, setBusy] = useState(false), [tick, setTick] = useState(0); const posting = useRef(false);
  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const id = installationId(await AsyncStorage.getItem(INSTALLATION_KEY)); await AsyncStorage.setItem(INSTALLATION_KEY, id);
        const restored = parseSavedReport(await AsyncStorage.getItem(REPORT_KEY));
        if (active) {
          setInstallation(id); setSaved(restored);
          if (restored) { setCell(restored.request.cell_id); setAnswer(restored.request.answer); setConsent(restored.request.consent_training); }
        }
      } catch { if (active) setStorageError(true); }
    })();
    return () => { active = false; };
  }, []);
  useEffect(() => {
    const abort = new AbortController();
    void requestCommunity(`state${cell ? `?cell_id=${encodeURIComponent(cell)}` : ''}`, undefined, abort.signal).then(parseCommunityState)
      .then(value => { if (!abort.signal.aborted) { setState(value); setLoading(false); } })
      .catch(() => { if (!abort.signal.aborted) { setLoadError(true); setLoading(false); } });
    return () => abort.abort();
  }, [cell, tick]);
  const locked = busy || Boolean(saved), selected = state?.cells.find(item => item.id === cell);
  function refresh() { setLoading(true); setLoadError(false); setTick(value => value + 1); }
  async function send() {
    if (posting.current || !installation || storageError || (!saved && (!cell || !answer || !here))) return;
    posting.current = true; setBusy(true); setError('');
    try {
      const record = saved ?? { request: parseReport({ request_id: reportUUID(), installation_id: installation, cell_id: cell, answer, observed_at_utc: new Date().toISOString(), consent_training: consent }), receipt: null };
      try { await AsyncStorage.setItem(REPORT_KEY, JSON.stringify(record)); } catch { setStorageError(true); return; }
      setSaved(record);
      const receipt = parseReceipt(await requestCommunity('reports', record.request));
      const complete = { ...record, receipt }; setSaved(complete);
      try { await AsyncStorage.setItem(REPORT_KEY, JSON.stringify(complete)); } catch { setStorageError(true); }
      refresh();
    } catch (e) { setError(e instanceof Error ? e.message : 'Request failed'); }
    finally { posting.current = false; setBusy(false); }
  }
  async function reset() {
    try { await AsyncStorage.removeItem(REPORT_KEY); setSaved(null); setAnswer(null); setConsent(false); setHere(false); setError(''); }
    catch { setStorageError(true); }
  }
  return <Card>
    <Copy accessibilityRole="header" style={styles.heading}>{copy('communityTitle')}</Copy>
    <Copy style={styles.small}>{copy('communityPrivacy')}</Copy>
    <Copy style={{ fontWeight: '700' }}>{copy('communityPlace')}</Copy><Copy style={styles.small}>{copy('communityPlaceHint')}</Copy>
    <View accessibilityRole="radiogroup" accessibilityLabel={copy('communityPlace')} style={{ gap: 8 }}>
      {state?.cells.map(item => <Pressable key={item.id} accessibilityRole="radio" accessibilityLabel={item.name} accessibilityState={{ checked: cell === item.id, disabled: locked || loading }} disabled={locked || loading} onPress={() => { if (cell !== item.id) { setLoading(true); setLoadError(false); setCell(item.id); } setHere(false); }} style={{ minHeight: 48, borderWidth: 1, borderColor: cell === item.id ? colors.teal : colors.line, backgroundColor: cell === item.id ? '#EAF1EE' : colors.white, borderRadius: 10, padding: 12 }}><Copy>{item.name}</Copy></Pressable>)}
    </View>
    {selected && <Copy style={styles.small}>{selected.bbox.join(', ')} (W, S, E, N)</Copy>}
    <Pressable accessibilityRole="checkbox" accessibilityLabel={copy('communityHere')} accessibilityState={{ checked: here, disabled: locked }} disabled={locked} onPress={() => setHere(value => !value)} style={{ minHeight: 48, flexDirection: 'row', gap: 10, alignItems: 'center' }}><Copy>{here ? '☑' : '☐'}</Copy><Copy style={{ flex: 1 }}>{copy('communityHere')}</Copy></Pressable>
    <Copy style={styles.heading}>{copy('communityQuestion')}</Copy>
    <View accessibilityRole="radiogroup" accessibilityLabel={copy('communityQuestion')} style={styles.row}>{(Object.keys(answerKeys) as Answer[]).map(value => <Pressable key={value} accessibilityRole="radio" accessibilityLabel={copy(answerKeys[value])} accessibilityState={{ checked: answer === value, disabled: locked || loading }} disabled={locked || loading} onPress={() => setAnswer(value)} style={{ minHeight: 48, padding: 12, borderWidth: 1, borderRadius: 10, borderColor: answer === value ? colors.teal : colors.line, backgroundColor: answer === value ? '#EAF1EE' : colors.white }}><Copy>{copy(answerKeys[value])}</Copy></Pressable>)}</View>
    <Pressable accessibilityRole="checkbox" accessibilityLabel={copy('communityConsent')} accessibilityState={{ checked: consent, disabled: locked }} disabled={locked} onPress={() => setConsent(value => !value)} style={{ minHeight: 48, flexDirection: 'row', gap: 10, alignItems: 'center' }}><Copy>{consent ? '☑' : '☐'}</Copy><Copy style={{ flex: 1 }}>{copy('communityConsent')}</Copy></Pressable>
    {saved && <Copy style={styles.small}>{`${copy('communityRestored')} ${saved.request.observed_at_utc} · ${copy(answerKeys[saved.request.answer])}`}</Copy>}
    {storageError && <Copy accessibilityRole="alert" style={styles.small}>{copy('communityStorageError')}</Copy>}
    {loadError && <Copy accessibilityRole="alert" style={styles.small}>{copy('apiError')}</Copy>}
    {!!error && <Copy accessibilityRole="alert" style={styles.small}>{`${copy('communityError')} ${error}`}</Copy>}
    {saved?.receipt ? <Copy accessibilityLiveRegion="polite">{`${copy('communitySaved')} ${saved.receipt.report_id}`}</Copy> : <Button label={copy(busy ? 'communitySending' : saved ? 'retry' : 'communitySend')} onPress={() => { void send(); }} disabled={busy || loading || loadError || storageError || !installation || !state?.enabled || (!saved && (!cell || !answer || !here))} />}
    {loading && <Copy accessibilityLiveRegion="polite" style={styles.small}>{copy('loading')}</Copy>}
    {!loading && state && !state.enabled && <Copy style={styles.small}>{copy('communityDisabled')}</Copy>}
    {saved && <Button secondary label={copy('communityReset')} disabled={busy} onPress={() => { void reset(); }} />}
    <Copy style={styles.small}>{copy('communityRetryHint')}</Copy>
    <Button secondary label={copy('retry')} disabled={loading} onPress={refresh} />
    {state && <><View style={styles.separator} /><Copy accessibilityRole="header" style={styles.heading}>{copy('communityAggregate')}</Copy><Copy style={styles.small}>{state.cells.find(c => c.id === state.selected_cell)?.name}</Copy><Copy>{copy(state.aggregate.public_status === 'collecting' ? 'pending' : 'communitySaved')}</Copy><Copy style={styles.small}>{copy('communityUnverified')}</Copy></>}
  </Card>;
}
