import { useMemo, useState } from 'react';
import { Linking, Pressable, TextInput, View, StyleSheet } from 'react-native';
import places from '../../../shared/locations.json';
import { Brand, Button, Card, Copy, Screen, colors, styles } from '../components/ui';
import { Earth } from '../components/earth';
import { SpeechButton } from '../components/speech-button';
import { CitizenReport } from '../components/citizen-report';
import { usePreferences } from '../state/preferences';
import { useForegroundLocation } from '../hooks/use-foreground-location';
import type { CopyKey } from '../../../shared/translations';
import type { LocationPhase } from '../lib/foreground-location';

const locationStatusCopy: Partial<Record<LocationPhase, CopyKey>> = { requesting: 'requestingLocation', finding: 'findingLocation', ready: 'locationReady', denied: 'locationDenied', unavailable: 'locationUnavailable', cancelled: 'locationCancelled', stale: 'locationStale', inaccurate: 'locationInaccurate' };

export default function PublicScreen() {
  const { copy, rtl, locale } = usePreferences();
  const [place, setPlace] = useState(places[0]);
  const location = useForegroundLocation();
  const target = useMemo(() => location.fix ? { lat: location.fix.lat, lon: location.fix.lon } : place, [location.fix, place]);
  const placeName = location.fix ? copy('deviceLocation') : place.name;
  const statusKey = locationStatusCopy[location.phase] ?? (location.permission === 'granted' ? 'permissionGranted' : location.permission === 'denied' ? 'locationDenied' : 'permissionUnknown');
  const [query, setQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [linkError, setLinkError] = useState(false);
  const matches = useMemo(() => places.filter(item => [item.name, item.state, ...item.aliases].some(value => value.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()))), [query]);
  return <Screen>
    <Brand />
    <View style={{ gap: 7 }}><Copy style={styles.eyebrow}>{copy('offline')}</Copy><Copy accessibilityRole="header" style={styles.title}>{copy('homeTitle')}</Copy><Copy style={styles.subtitle}>{copy('homeSubtitle')}</Copy></View>
    <Card>
      <Copy style={styles.heading}>{copy('useLocation')}</Copy><Copy style={styles.small}>{copy('locationPurpose')}</Copy>
      <Button label={copy(location.busy ? 'cancelLocation' : 'useLocation')} onPress={() => { if (location.busy) location.cancel(); else void location.request(); }} />
      <Copy accessibilityLiveRegion="polite" style={styles.small}>{copy(statusKey)}</Copy>
      {location.permission === 'granted' && statusKey !== 'permissionGranted' && <Copy style={styles.small}>{copy('permissionGranted')}</Copy>}
    </Card>
    <View style={{ gap: 9 }}><Copy style={[styles.small, { fontWeight: '700' }]}>{copy('search')}</Copy><TextInput accessibilityLabel={copy('search')} placeholder={copy('searchPlaceholder')} placeholderTextColor={colors.muted} value={query} onFocus={() => setSearching(true)} onChangeText={text => { setQuery(text); setSearching(true); }} style={[local.search, rtl && { writingDirection: 'rtl', textAlign: 'right' }]} autoCorrect={false} returnKeyType="search" />
      {searching && <Card style={{ gap: 0, padding: 8 }}>
        {matches.slice(0, 6).map(item => <Pressable key={item.id} accessibilityRole="button" accessibilityLabel={`${item.name}, ${item.state}`} onPress={() => { location.reset(); setPlace(item); setQuery(''); setSearching(false); }} style={({ pressed }) => [local.result, pressed && { backgroundColor: '#EAF1EE' }]}><Copy style={{ fontWeight: '600' }}>{item.name}</Copy><Copy style={styles.small}>{item.state}</Copy></Pressable>)}
        {!matches.length && <Copy style={{ padding: 10 }}>{copy('noResults')}</Copy>}
        <Button secondary label={copy('close')} onPress={() => setSearching(false)} />
      </Card>}
    </View>
    <Earth target={target} name={placeName} />
    <Card>
      <Copy style={styles.eyebrow}>{copy(location.fix ? 'deviceLocation' : 'manualLocation')}</Copy>
      <Copy>{`${target.lat.toFixed(4)}°, ${target.lon.toFixed(4)}°`}</Copy>
      {location.fix ? <>
        <Copy style={styles.small}>{copy('regionUnknown')}</Copy>
        <Copy style={styles.small}>{`${copy('locationAccuracy')}: ±${Math.round(location.fix.accuracy)} m`}</Copy>
        <Copy style={styles.small}>{`${copy('locationCaptured')}: ${new Date(location.fix.timestamp).toLocaleString(locale)}`}</Copy>
        {location.phase === 'stale' && <Copy style={styles.small}>{copy('locationStale')}</Copy>}
        <Button secondary label={copy('clearLocation')} onPress={location.reset} />
      </> : <><Copy style={styles.small}>{`${place.name}, ${place.state} · IN`}</Copy><Copy style={styles.small}>{copy('manualPointNote')}</Copy></>}
      <View style={styles.separator} /><Copy>{copy('liveCoverageUnavailable')}</Copy>
    </Card>
    <Card style={{ borderColor: '#E4D4AA', backgroundColor: '#FFF9EB' }}><Copy style={styles.pill}>{copy('preview')}</Copy><Copy style={styles.small}>{copy('currentUnavailable')}</Copy><Copy accessibilityRole="header" style={styles.heading}>{copy('practiceTitle')}</Copy><Copy>{copy('practiceBody')}</Copy><SpeechButton id="practice-v1" text={`${copy('preview')}. ${copy('practiceBody')}`} /></Card>
    <CitizenReport />
    <Card><Copy accessibilityRole="header" style={styles.heading}>{copy('guideTitle')}</Copy><Copy>{copy('guideBody')}</Copy><Button secondary icon="arrow" label={copy('officialWarnings')} onPress={() => { setLinkError(false); void Linking.openURL('https://sachet.ndma.gov.in/').catch(() => setLinkError(true)); }} />{linkError && <Copy accessibilityLiveRegion="polite" style={styles.small}>{copy('apiError')}</Copy>}</Card>
  </Screen>;
}
const local = StyleSheet.create({ search: { backgroundColor: colors.white, borderWidth: 1, borderColor: colors.line, borderRadius: 14, padding: 16, minHeight: 54, fontSize: 15, color: colors.ink }, result: { padding: 12, borderRadius: 9, minHeight: 55 } });
