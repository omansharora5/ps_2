import { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Linking, View } from 'react-native';
import { apiBase, parseCatalog, parseSimulation, requestApi, safeExternalUrl, type Catalog, type Simulation } from '../lib/api';
import { Brand, Button, Card, Copy, Screen, colors, styles } from '../components/ui';
import { SpeechButton } from '../components/speech-button';
import { usePreferences } from '../state/preferences';

export default function OperatorScreen() {
  const { copy } = usePreferences();
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [run, setRun] = useState<Simulation | null>(null);
  const [loading, setLoading] = useState(Boolean(apiBase));
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(false);
  const [runError, setRunError] = useState(false);
  const [linkError, setLinkError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const runAbort = useRef<AbortController | null>(null);
  useEffect(() => {
    if (!apiBase) return;
    const abort = new AbortController();
    requestApi('/api/data/catalog', abort.signal).then(value => { if (!abort.signal.aborted) setCatalog(parseCatalog(value)); }).catch(() => { if (!abort.signal.aborted) setError(true); }).finally(() => { if (!abort.signal.aborted) setLoading(false); });
    return () => abort.abort();
  }, [attempt]);
  useEffect(() => () => runAbort.current?.abort(), []);
  const runExperiment = async () => {
    runAbort.current?.abort();
    const abort = new AbortController(); runAbort.current = abort;
    setRun(null); setRunError(false); setRunning(true);
    try { const value = await requestApi('/api/runs', abort.signal); if (!abort.signal.aborted) setRun(parseSimulation(value)); }
    catch { if (!abort.signal.aborted) setRunError(true); }
    finally { if (!abort.signal.aborted) setRunning(false); }
  };
  const summary = run ? `${copy('synthetic')}. ${copy('simulationBody')}` : '';
  return <Screen><Brand /><View style={{ gap: 7 }}><Copy style={styles.eyebrow}>{copy('operatorView')}</Copy><Copy accessibilityRole="header" style={styles.title}>{copy('operatorTitle')}</Copy><Copy style={styles.subtitle}>{copy('operatorBody')}</Copy></View>
    {!apiBase && <Card><Copy style={styles.pill}>{copy('offline')}</Copy><Copy>{copy('connectHint')}</Copy></Card>}
    <Card><Copy style={styles.pill}>{copy('synthetic')}</Copy><Copy>{copy('simulationBody')}</Copy><Button label={running ? copy('loading') : copy('runSimulation')} disabled={!apiBase || running} icon="lab" onPress={() => { void runExperiment(); }} />
      {runError && <Copy accessibilityLiveRegion="polite">{copy('apiError')}</Copy>}
      {run && <View style={{ gap: 14 }}><View style={styles.separator} /><Copy style={styles.small}>{run.time_note}</Copy><Copy style={styles.small}>{`Target: ${run.target}\nLead: +${run.horizon} min\nIssue: ${run.issued_at}\nValid: ${run.valid_at}`}</Copy>{run.sites.map(site => <View key={site.id} style={{ gap: 2 }}><Copy style={{ fontWeight: '700' }}>{site.name}</Copy><View style={[styles.row, { justifyContent: 'space-between' }]}><Copy style={styles.small}>{copy('probability')}</Copy><Copy style={styles.heading}>{site.probability === null ? '—' : `${Math.round(site.probability * 100)}%`}</Copy></View></View>)}<SpeechButton id={run.id} text={summary} /></View>}
    </Card>
    <View style={{ gap: 9 }}><Copy accessibilityRole="header" style={styles.heading}>{copy('sourceCatalogue')}</Copy><Copy style={styles.small}>{copy('dataScope')}</Copy></View>
    {loading && <ActivityIndicator accessibilityLabel={copy('loading')} color={colors.teal} />}
    {error && <Card><Copy accessibilityLiveRegion="polite">{copy('apiError')}</Copy><Button secondary label={copy('retry')} onPress={() => { setLoading(true); setError(false); setAttempt(value => value + 1); }} /></Card>}
    {catalog?.collections.map(collection => <Card key={collection.id}><View style={[styles.row, { justifyContent: 'space-between' }]}><Copy style={styles.heading}>{collection.name}</Copy><Copy style={styles.pill}>{copy(collection.status === 'available' ? 'available' : 'pending')}</Copy></View><Copy style={styles.small}>{copy('files')}: {collection.local_file_count} · {(collection.bytes / 1024 / 1024).toFixed(1)} MB</Copy></Card>)}
    {catalog?.sources.map(source => <Card key={source.id}><Copy style={{ fontWeight: '700' }}>{source.name}</Copy><Copy style={styles.small}>{source.provider}</Copy><Copy style={styles.small}>{copy('files')}: {source.local_file_count}</Copy>{safeExternalUrl(source.source_url) && <Button secondary label={copy('openSource')} accessibilityLabel={`${copy('openSource')}: ${source.name}`} icon="arrow" onPress={() => { setLinkError(false); void Linking.openURL(source.source_url).catch(() => setLinkError(true)); }} />}</Card>)}
    {linkError && <Copy accessibilityLiveRegion="polite">{copy('apiError')}</Copy>}
  </Screen>;
}
