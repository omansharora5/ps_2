import { Pressable, ScrollView, StyleSheet, Text, View, type ColorValue, type TextProps, type ViewProps } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Svg, { Path, Circle } from 'react-native-svg';
import { usePreferences } from '../state/preferences';

export const colors = { ink: '#142C3B', muted: '#546875', paper: '#F3F6F4', line: '#D9E2E1', navy: '#071F32', teal: '#0D6B61', mint: '#ACF0D0', amber: '#FFDF91', white: '#FFFFFF' };
export function Copy({ style, ...props }: TextProps) {
  const { rtl } = usePreferences();
  return <Text {...props} style={[styles.text, rtl && { writingDirection: 'rtl', textAlign: 'right' }, style]} />;
}
export function Icon({ name, color = colors.ink, size = 22 }: { name: 'earth' | 'lab' | 'language' | 'arrow' | 'speaker' | 'stop' | 'check'; color?: ColorValue; size?: number }) {
  const paths = {
    earth: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20M2 12h20M12 2c-6 6-6 14 0 20 6-6 6-14 0-20',
    lab: 'M8 3h8M10 3v7L4 20h16l-6-10V3M7 15h10',
    language: 'M3 4h12M9 2v2M5 4c1 6 4 9 9 11M13 4c-1 6-4 9-10 12M13 21l4-11 4 11M14 18h6',
    arrow: 'M5 12h14M13 6l6 6-6 6',
    speaker: 'M4 9v6h4l5 4V5L8 9H4M17 8c3 2 3 6 0 8M20 5c5 4 5 10 0 14',
    stop: 'M6 6h12v12H6Z',
    check: 'M5 12l4 4L19 6',
  };
  return <Svg width={size} height={size} viewBox="0 0 24 24" aria-hidden><Path d={paths[name]} stroke={color} strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" fill="none" /></Svg>;
}
export function Screen({ children }: { children: React.ReactNode }) {
  return <SafeAreaView style={styles.safe} edges={['top', 'left', 'right']}><ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={styles.scroll}><View style={styles.content}>{children}</View></ScrollView></SafeAreaView>;
}
export function Brand() {
  return <View style={styles.brand}><View style={styles.logo}><Svg width={22} height={26} viewBox="0 0 22 26"><Path d="M13 1 2 15h8l-1 10L21 9h-9Z" fill={colors.mint} /></Svg></View><Copy style={styles.wordmark}>VAJRA</Copy><View style={styles.brandLine} /><CircleDot /></View>;
}
function CircleDot() { return <Svg width={9} height={9}><Circle cx={4.5} cy={4.5} r={4.5} fill={colors.teal} /></Svg>; }
export function Card({ style, ...props }: ViewProps) { return <View {...props} style={[styles.card, style]} />; }
export function Button({ label, onPress, disabled, secondary, icon, accessibilityLabel }: { label: string; onPress: () => void; disabled?: boolean; secondary?: boolean; icon?: Parameters<typeof Icon>[0]['name']; accessibilityLabel?: string }) {
  return <Pressable accessibilityRole="button" accessibilityLabel={accessibilityLabel ?? label} accessibilityState={{ disabled: !!disabled }} disabled={disabled} onPress={onPress} style={({ pressed }) => [styles.button, secondary && styles.secondary, disabled && { opacity: 0.5 }, pressed && { opacity: 0.78 }]}>{icon && <Icon name={icon} color={secondary ? colors.ink : colors.white} size={19} />}<Copy style={[styles.buttonText, secondary && { color: colors.ink }]}>{label}</Copy></Pressable>;
}
export const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.paper }, scroll: { flexGrow: 1, alignItems: 'center' }, content: { width: '100%', maxWidth: 660, padding: 22, paddingBottom: 34, gap: 20 },
  text: { fontSize: 15, color: colors.ink, lineHeight: 23 }, brand: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 6 }, logo: { width: 39, height: 42, borderRadius: 12, backgroundColor: colors.navy, alignItems: 'center', justifyContent: 'center' }, wordmark: { fontWeight: '800', fontSize: 21, letterSpacing: 3 }, brandLine: { flex: 1, height: 1, backgroundColor: colors.line, marginHorizontal: 10 },
  eyebrow: { fontSize: 11, fontWeight: '800', letterSpacing: 1.5, color: colors.teal, textTransform: 'uppercase' }, title: { fontSize: 34, lineHeight: 42, letterSpacing: -1, fontWeight: '700' }, subtitle: { fontSize: 15, color: colors.muted, lineHeight: 24 }, heading: { fontSize: 21, lineHeight: 29, fontWeight: '700' }, card: { backgroundColor: colors.white, borderWidth: 1, borderColor: colors.line, borderRadius: 22, padding: 20, gap: 12 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 10, flexWrap: 'wrap' }, button: { minHeight: 48, borderRadius: 14, backgroundColor: colors.teal, paddingHorizontal: 18, paddingVertical: 12, alignItems: 'center', justifyContent: 'center', flexDirection: 'row', gap: 10 }, secondary: { backgroundColor: '#EAF1EE' }, buttonText: { color: colors.white, fontWeight: '700', fontSize: 14, flexShrink: 1 }, small: { fontSize: 12, lineHeight: 19, color: colors.muted }, pill: { alignSelf: 'flex-start', borderRadius: 8, backgroundColor: '#FFF0C8', paddingVertical: 5, paddingHorizontal: 9, color: '#644F13', fontSize: 11, lineHeight: 17, fontWeight: '700' }, separator: { height: 1, backgroundColor: colors.line },
});
