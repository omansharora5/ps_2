import { useEffect, useMemo, useRef, useState } from 'react';
import { Animated, AppState, Easing, View, StyleSheet } from 'react-native';
import { useIsFocused } from 'expo-router';
import Svg, { Circle, Defs, G, Path, RadialGradient, Stop, Text as SvgText } from 'react-native-svg';
import land from '../../../shared/earth-land.json';
import { interpolateFocus, projectPoint, type Focus } from '../../../shared/earth-math';
import { usePreferences } from '../state/preferences';
import { Button, Copy, colors, styles } from './ui';

const R = 134;
function linePath(points: number[][], focus: Focus) {
  let path = ''; let drawing = false;
  for (const [lon, lat] of points) {
    const p = projectPoint(lat, lon, focus);
    if (p.z < 0) { drawing = false; continue; }
    path += `${drawing ? 'L' : 'M'}${(160 + R * p.x).toFixed(1)},${(160 + R * p.y).toFixed(1)}`;
    drawing = true;
  }
  return path;
}
const grid: number[][][] = [];
for (let lat = -60; lat <= 60; lat += 30) grid.push(Array.from({ length: 121 }, (_, i) => [-180 + i * 3, lat]));
for (let lon = -180; lon < 180; lon += 30) grid.push(Array.from({ length: 61 }, (_, i) => [lon, -90 + i * 3]));

export function Earth({ target, name }: { target: Focus; name: string }) {
  const { copy, reducedMotion } = usePreferences();
  const focused = useIsFocused();
  const [paused, setPaused] = useState(false);
  const [active, setActive] = useState(AppState.currentState === 'active');
  const [focus, setFocus] = useState<Focus>({ lat: 10, lon: 40 });
  const focusRef = useRef(focus);
  const [zoom, setZoom] = useState(0.87);
  const [drift] = useState(() => new Animated.Value(0));
  const motion = !paused && !reducedMotion && active && focused;
  useEffect(() => { const sub = AppState.addEventListener('change', value => setActive(value === 'active')); return () => sub.remove(); }, []);
  useEffect(() => {
    if (!motion) { focusRef.current = target; return; }
    const from = focusRef.current; const start = Date.now();
    const timer = setInterval(() => {
      const progress = Math.min(1, (Date.now() - start) / 950);
      const eased = 1 - (1 - progress) ** 3;
      const next = interpolateFocus(from, target, eased);
      focusRef.current = next; setFocus(next); setZoom(0.87 + eased * 0.13);
      if (progress === 1) clearInterval(timer);
    }, 45);
    return () => clearInterval(timer);
  }, [target, motion]);
  useEffect(() => {
    if (!motion) return;
    const loop = Animated.loop(Animated.timing(drift, { toValue: 1, duration: 60000, easing: Easing.linear, useNativeDriver: true }));
    loop.start();
    return () => { loop.stop(); drift.setValue(0); };
  }, [motion, drift]);
  const displayedFocus = motion ? focus : target;
  const displayedZoom = motion ? zoom : 1;
  const coastline = useMemo(() => land.map(points => linePath(points, displayedFocus)).join(''), [displayedFocus]);
  const graticule = useMemo(() => grid.map(points => linePath(points, displayedFocus)).join(''), [displayedFocus]);
  const marker = projectPoint(target.lat, target.lon, displayedFocus);
  return <View style={earthStyles.card}>
    <View style={earthStyles.labelRow}><Copy style={earthStyles.label}>{copy('search')}</Copy><Copy style={earthStyles.coordinates}>{target.lat.toFixed(2)}° · {target.lon.toFixed(2)}°</Copy></View>
    <View accessible accessibilityLabel={`${name}. ${copy('earthNote')}`} style={earthStyles.canvas}>
      <Svg width="100%" height="100%" viewBox="0 0 320 320">
        <Defs><RadialGradient id="ocean" cx="35%" cy="25%" r="80%"><Stop offset="0" stopColor="#286E82" /><Stop offset="0.6" stopColor="#103B53" /><Stop offset="1" stopColor="#061522" /></RadialGradient></Defs>
        <Circle cx={160} cy={160} r={153} stroke="#295168" strokeWidth={0.5} strokeDasharray="2 8" fill="none" />
        <G transform={`translate(${160 * (1 - displayedZoom)} ${160 * (1 - displayedZoom)}) scale(${displayedZoom})`}>
          <Circle cx={160} cy={160} r={R + 5} fill="none" stroke="#4CB5AE" strokeOpacity={0.22} strokeWidth={7} />
          <Circle cx={160} cy={160} r={R} fill="url(#ocean)" stroke="#65B3AE" strokeWidth={1} />
          <Path d={graticule} stroke="#A9D0D0" strokeWidth={0.45} strokeOpacity={0.21} fill="none" />
          <Path d={coastline} stroke="#9AD7B5" strokeWidth={0.9} strokeOpacity={0.95} fill="none" />
          {marker.z >= 0 && <G><Circle cx={160 + marker.x * R} cy={160 + marker.y * R} r={11} fill="#FFE19A" fillOpacity={0.15} /><Circle cx={160 + marker.x * R} cy={160 + marker.y * R} r={4} fill="#FFE19A" stroke="#FFFFFF" strokeWidth={1.5} /></G>}
        </G>
        <SvgText x={160} y={312} textAnchor="middle" fill="#90B4C2" fontSize={8} letterSpacing={3}>NATURAL EARTH</SvgText>
      </Svg>
      <Animated.View pointerEvents="none" style={[StyleSheet.absoluteFill, { opacity: 0.22, transform: [{ rotate: drift.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '360deg'] }) }] }]}>
        <Svg width="100%" height="100%" viewBox="0 0 320 320"><Path d="M81 100q47-21 94-4M104 111q34-8 54-3M168 209q35 9 62-6M176 218q19 7 35 2" stroke="#DAF5F1" strokeWidth={7} strokeLinecap="round" fill="none" /></Svg>
      </Animated.View>
    </View>
    <Copy style={earthStyles.place}>{name}</Copy>
    <Copy style={[styles.small, { color: '#B4CBD1' }]}>{copy('earthNote')}</Copy>
    {reducedMotion ? <Copy style={[styles.small, { color: colors.mint }]}>{copy('motionReduced')}</Copy> : <Button secondary label={copy(paused ? 'resumeMotion' : 'pauseMotion')} onPress={() => setPaused(value => !value)} />}
  </View>;
}
const earthStyles = StyleSheet.create({ card: { backgroundColor: colors.navy, borderRadius: 26, padding: 20, gap: 10, overflow: 'hidden' }, canvas: { aspectRatio: 1, width: '100%', maxWidth: 370, alignSelf: 'center' }, labelRow: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', gap: 8 }, label: { fontSize: 11, color: colors.mint, fontWeight: '700', letterSpacing: 0.7 }, coordinates: { color: '#93B1C0', fontSize: 11, fontVariant: ['tabular-nums'] }, place: { color: colors.white, fontSize: 26, lineHeight: 32, fontWeight: '600' } });
