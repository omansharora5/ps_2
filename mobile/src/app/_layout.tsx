import { Tabs } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { ActivityIndicator, View, useWindowDimensions } from 'react-native';
import { SafeAreaProvider, useSafeAreaInsets } from 'react-native-safe-area-context';
import { PreferencesProvider, usePreferences } from '../state/preferences';
import { colors, Icon } from '../components/ui';

function Navigation() {
  const { copy, ready } = usePreferences();
  const insets = useSafeAreaInsets();
  const { fontScale } = useWindowDimensions();
  const bottomPadding = Math.max(insets.bottom, 10);
  const itemHeight = Math.max(56, Math.ceil(30 + 20 * fontScale));
  if (!ready) return <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.paper }}><ActivityIndicator accessibilityLabel={copy('loading')} color={colors.teal} /></View>;
  return <><StatusBar style="dark" /><Tabs screenOptions={{ headerShown: false, tabBarActiveTintColor: colors.teal, tabBarInactiveTintColor: colors.muted, tabBarStyle: { backgroundColor: colors.white, borderTopColor: colors.line, height: itemHeight + 9 + bottomPadding, paddingTop: 8, paddingBottom: bottomPadding }, tabBarLabelPosition: 'below-icon', tabBarLabelStyle: { fontSize: 11, lineHeight: 18, marginTop: 3, fontWeight: '600' }, tabBarItemStyle: { minHeight: itemHeight } }}>
    <Tabs.Screen name="index" options={{ title: copy('publicView'), tabBarIcon: ({ color }) => <Icon name="earth" color={color} /> }} />
    <Tabs.Screen name="operator" options={{ title: copy('operatorView'), tabBarIcon: ({ color }) => <Icon name="lab" color={color} /> }} />
    <Tabs.Screen name="language" options={{ title: copy('language'), tabBarIcon: ({ color }) => <Icon name="language" color={color} /> }} />
  </Tabs></>;
}
export default function RootLayout() { return <SafeAreaProvider><PreferencesProvider><Navigation /></PreferencesProvider></SafeAreaProvider>; }
