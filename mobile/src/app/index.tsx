import { useMemo, useState } from 'react';
import { Linking, Pressable, TextInput, View, StyleSheet } from 'react-native';
import places from '../../../shared/locations.json';
import { Brand, Button, Card, Copy, Screen, colors, styles } from '../components/ui';
import { Earth } from '../components/earth';
import { SpeechButton } from '../components/speech-button';
import { usePreferences } from '../state/preferences';

export default function PublicScreen() {
  const { copy, rtl } = usePreferences();
  const [place, setPlace] = useState(places[0]);
  const [query, setQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [linkError, setLinkError] = useState(false);
  const matches = useMemo(() => places.filter(item => [item.name, item.state, ...item.aliases].some(value => value.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()))), [query]);
  return <Screen>
    <Brand />
    <View style={{ gap: 7 }}><Copy style={styles.eyebrow}>{copy('offline')}</Copy><Copy accessibilityRole="header" style={styles.title}>{copy('homeTitle')}</Copy><Copy style={styles.subtitle}>{copy('homeSubtitle')}</Copy></View>
    <View style={{ gap: 9 }}><Copy style={[styles.small, { fontWeight: '700' }]}>{copy('search')}</Copy><TextInput accessibilityLabel={copy('search')} placeholder={copy('searchPlaceholder')} placeholderTextColor={colors.muted} value={query} onFocus={() => setSearching(true)} onChangeText={text => { setQuery(text); setSearching(true); }} style={[local.search, rtl && { writingDirection: 'rtl', textAlign: 'right' }]} autoCorrect={false} returnKeyType="search" />
      {searching && <Card style={{ gap: 0, padding: 8 }}>
        {matches.slice(0, 6).map(item => <Pressable key={item.id} accessibilityRole="button" accessibilityLabel={`${item.name}, ${item.state}`} onPress={() => { setPlace(item); setQuery(''); setSearching(false); }} style={({ pressed }) => [local.result, pressed && { backgroundColor: '#EAF1EE' }]}><Copy style={{ fontWeight: '600' }}>{item.name}</Copy><Copy style={styles.small}>{item.state}</Copy></Pressable>)}
        {!matches.length && <Copy style={{ padding: 10 }}>{copy('noResults')}</Copy>}
        <Button secondary label={copy('close')} onPress={() => setSearching(false)} />
      </Card>}
    </View>
    <Earth target={place} name={place.name} />
    <Card style={{ borderColor: '#E4D4AA', backgroundColor: '#FFF9EB' }}><Copy style={styles.pill}>{copy('preview')}</Copy><Copy style={styles.small}>{copy('currentUnavailable')}</Copy><Copy accessibilityRole="header" style={styles.heading}>{copy('practiceTitle')}</Copy><Copy>{copy('practiceBody')}</Copy><SpeechButton id="practice-v1" text={`${copy('preview')}. ${copy('practiceBody')}`} /></Card>
    <Card><Copy accessibilityRole="header" style={styles.heading}>{copy('guideTitle')}</Copy><Copy>{copy('guideBody')}</Copy><Button secondary icon="arrow" label={copy('officialWarnings')} onPress={() => { setLinkError(false); void Linking.openURL('https://sachet.ndma.gov.in/').catch(() => setLinkError(true)); }} />{linkError && <Copy accessibilityLiveRegion="polite" style={styles.small}>{copy('apiError')}</Copy>}</Card>
  </Screen>;
}
const local = StyleSheet.create({ search: { backgroundColor: colors.white, borderWidth: 1, borderColor: colors.line, borderRadius: 14, padding: 16, minHeight: 54, fontSize: 15, color: colors.ink }, result: { padding: 12, borderRadius: 9, minHeight: 55 } });
