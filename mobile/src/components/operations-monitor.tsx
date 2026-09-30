import { useCallback, useMemo, useState } from 'react';
import { useFocusEffect } from 'expo-router';
import { ActivityIndicator, AppState, View } from 'react-native';
import { apiBase, requestApi } from '../lib/api';
import { createOperationsMonitor, EMPTY_OPERATIONS, latestCandidate, recentJobs, utcTime, type OperationJob } from '../lib/operations';
import { usePreferences } from '../state/preferences';
import { Button, Card, Copy, colors, styles } from './ui';

const kindCopy = { starter_audit: 'opsAudit', radar_replay: 'opsReplay', train_candidate: 'opsTrain' } as const;
const statusCopy = { queued: 'opsQueued', running: 'opsRunning', succeeded: 'opsSucceeded', failed: 'opsFailed', cancelled: 'opsCancelled' } as const;

function JobRow({ job }: { job: OperationJob }) {
  const { copy } = usePreferences();
  return <View style={{ gap: 8 }}>
    <View style={[styles.row, { justifyContent: 'space-between' }]}>
      <Copy style={{ flexShrink: 1, fontWeight: '700' }}>{copy(kindCopy[job.kind])}</Copy>
      <Copy style={styles.pill}>{copy(statusCopy[job.status])}</Copy>
    </View>
    <Copy style={styles.small}>{copy('opsStage')}: {job.stage}</Copy>
    <Copy selectable style={styles.small}>{job.scope}{'\n'}{job.id}</Copy>
    <Copy style={styles.small}>{copy('opsUpdated')}: {utcTime(job.updated_at)}</Copy>
    {job.error && <Copy selectable style={styles.small}>{job.error}</Copy>}
  </View>;
}

export function OperationsMonitor() {
  const { copy } = usePreferences();
  const [state, setState] = useState(EMPTY_OPERATIONS);
  const [expanded, setExpanded] = useState(false);
  const monitor = useMemo(() => createOperationsMonitor(signal => requestApi('/api/operations/state', signal), setState), []);
  useFocusEffect(useCallback(() => {
    if (apiBase && (AppState.currentState === 'active' || AppState.currentState === null)) void monitor.refresh();
    const subscription = AppState.addEventListener('change', next => { if (next !== 'active') monitor.pause(); });
    return () => { subscription.remove(); monitor.pause(); };
  }, [monitor]));
  const data = state.data;
  const jobs = data ? recentJobs(data.jobs) : [];
  const candidate = data ? latestCandidate(data.jobs) : undefined;
  const metrics = candidate?.summary;
  const loading = state.phase === 'loading';
  return <View style={{ gap: 12 }}>
    <Card accessibilityLabel={copy('opsTitle')}>
      <Copy style={styles.pill}>{copy('opsScope')}</Copy>
      <Copy accessibilityRole="header" style={styles.heading}>{copy('opsTitle')}</Copy>
      <Copy>{copy('opsReadOnly')}</Copy>
      <Copy style={styles.small}>{copy('currentUnavailable')}</Copy>
      <Button secondary label={loading ? copy('loading') : copy('opsRefresh')} disabled={!apiBase || loading} onPress={() => { void monitor.refresh(); }} />
      {loading && <ActivityIndicator accessibilityLabel={copy('loading')} color={colors.teal} />}
      {state.receivedAt !== null && <Copy style={styles.small}>{copy('opsSnapshot')}: {utcTime(state.receivedAt)}</Copy>}
      {state.phase === 'stale' && <Copy accessibilityLiveRegion="polite" style={styles.pill}>{copy('opsStale')}</Copy>}
      {state.phase === 'error' && <Copy accessibilityLiveRegion="polite">{copy('opsUnavailable')}</Copy>}
      {data && <>
        <View style={styles.separator} />
        <View style={{ gap: 5 }}><Copy style={{ fontWeight: '700' }}>{copy('opsWorker')}</Copy><Copy>{copy(data.worker.available ? 'opsWorkerReady' : 'opsWorkerMissing')}</Copy>{data.worker.last_seen_at && <Copy style={styles.small}>{utcTime(data.worker.last_seen_at)}</Copy>}</View>
        <View style={{ gap: 5 }}><Copy style={{ fontWeight: '700' }}>{copy('opsLearning')}: {copy(data.learning.enabled ? 'opsEnabled' : 'opsDisabled')}</Copy><Copy style={styles.small}>{copy('opsMetadata')}</Copy><Copy selectable style={styles.small}>{data.learning.status}{'\n'}{data.learning.note}</Copy>{data.learning.last_checked_at && <Copy style={styles.small}>{copy('opsUpdated')}: {utcTime(data.learning.last_checked_at)}</Copy>}</View>
      </>}
    </Card>
    {data && <>
      <Card>
        <Copy accessibilityRole="header" style={styles.heading}>{copy('opsCandidate')}</Copy>
        {metrics && candidate ? <>
          <Copy style={styles.pill}>{copy(metrics.recommendation === 'retain_baseline' ? 'opsRetain' : 'opsReview')}</Copy>
          <Copy style={styles.small}>{copy('opsBrier')}</Copy>
          {([
            ['opsRaw', metrics.raw_brier], ['opsCalibrated', metrics.calibrated_brier], ['opsBaseline', metrics.baseline_brier],
          ] as const).map(([key, value]) => <View key={key} style={[styles.row, { justifyContent: 'space-between' }]}><Copy style={{ flexShrink: 1 }}>{copy(key)}</Copy><Copy style={{ fontWeight: '700', fontVariant: ['tabular-nums'] }}>{value.toFixed(5)}</Copy></View>)}
          <Copy style={styles.small}>{copy('opsTestEvents')}: {metrics.test_event_count}</Copy>
          <Copy selectable style={styles.small}>{candidate.scope}{'\n'}{candidate.id}</Copy>
          <Copy style={styles.small}>{copy('opsNotPromoted')}</Copy>
        </> : <Copy style={styles.small}>{copy('opsNoCandidate')}</Copy>}
      </Card>
      <Card>
        <Copy accessibilityRole="header" style={styles.heading}>{copy('opsRecentJobs')} · {jobs.length}</Copy>
        {jobs.length === 0 && <Copy style={styles.small}>{copy('opsNoJobs')}</Copy>}
        {(expanded ? jobs : jobs.slice(0, 3)).map((job, index) => <View key={job.id} style={{ gap: 14 }}>{index > 0 && <View style={styles.separator} />}<JobRow job={job} /></View>)}
        {jobs.length > 3 && <Button secondary label={copy(expanded ? 'opsShowLess' : 'opsShowMore')} onPress={() => setExpanded(value => !value)} />}
      </Card>
      <Card>
        <Copy accessibilityRole="header" style={styles.heading}>{copy('opsDatasets')} · {data.datasets.length}</Copy>
        {data.datasets.length === 0 && <Copy style={styles.small}>{copy('opsNoDatasets')}</Copy>}
        {data.datasets.map((dataset, index) => <View key={dataset.id} style={{ gap: 8 }}>
          {index > 0 && <View style={styles.separator} />}
          <Copy style={{ fontWeight: '700' }}>{dataset.name}</Copy>
          <Copy style={styles.pill}>{copy(dataset.learning_eligible ? 'opsEligible' : 'opsNotReady')}</Copy>
          <Copy style={styles.small}>{copy('opsEvents')}: {dataset.event_count}</Copy>
          <Copy selectable style={styles.small}>{dataset.scope}{'\n'}{dataset.target}</Copy>
          {dataset.readiness_reasons.map((reason, reasonIndex) => <Copy selectable key={reasonIndex} style={styles.small}>• {reason}</Copy>)}
        </View>)}
      </Card>
    </>}
  </View>;
}
