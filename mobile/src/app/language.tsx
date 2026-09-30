import { Pressable, View, StyleSheet } from 'react-native';
import { LANGUAGES } from '../../../shared/translations';
import { Brand, Card, Copy, Icon, Screen, colors, styles } from '../components/ui';
import { SpeechButton } from '../components/speech-button';
import { usePreferences } from '../state/preferences';

export default function LanguageScreen() {
  const { language, setLanguage, copy, saved, storageError } = usePreferences();
  return <Screen><Brand /><View style={{ gap: 7 }}><Copy style={styles.eyebrow}>{copy('preferences')}</Copy><Copy accessibilityRole="header" style={styles.title}>{copy('language')}</Copy></View>
    <View style={local.grid}>{LANGUAGES.map(item => <Pressable key={item.code} accessibilityRole="button" accessibilityLabel={item.name} accessibilityState={{ selected: language === item.code }} onPress={() => setLanguage(item.code)} style={({ pressed }) => [local.item, language === item.code && local.selected, pressed && { opacity: 0.75 }]}><Copy style={[local.name, item.rtl && { writingDirection: 'rtl' }]}>{item.name}</Copy>{language === item.code && <Icon name="check" color={colors.teal} size={18} />}</Pressable>)}</View>
    {(saved || storageError) && <Copy accessibilityLiveRegion="polite" style={styles.small}>{copy(storageError ? 'storageFailed' : 'languageSaved')}</Copy>}
    <Card><Copy style={styles.pill}>{copy('preview')}</Copy><Copy>{copy('practiceBody')}</Copy><SpeechButton id="language-practice-v1" text={`${copy('preview')}. ${copy('practiceBody')}`} /></Card>
  </Screen>;
}
const local = StyleSheet.create({ grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 }, item: { width: '48%', flexGrow: 1, minHeight: 65, padding: 16, borderRadius: 16, backgroundColor: colors.white, borderWidth: 1, borderColor: colors.line, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 6 }, selected: { borderColor: colors.teal, backgroundColor: '#E2F4EB' }, name: { fontSize: 18, fontWeight: '600', flexShrink: 1, lineHeight: 29 } });
