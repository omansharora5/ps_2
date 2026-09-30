import { useCallback, useEffect, useMemo, useState } from 'react';
import { AppState } from 'react-native';
import { useFocusEffect } from 'expo-router';
import * as Location from 'expo-location';
import { createForegroundLocationController, type LocationSnapshot } from '../lib/foreground-location';

export function useForegroundLocation() {
  const [snapshot, setSnapshot] = useState<LocationSnapshot>({ phase: 'idle', permission: 'unknown' });
  const controller = useMemo(() => createForegroundLocationController({
    requestPermission: Location.requestForegroundPermissionsAsync,
    hasServices: Location.hasServicesEnabledAsync,
    watch: (success, error) => Location.watchPositionAsync({ accuracy: Location.Accuracy.Balanced, timeInterval: 1000, distanceInterval: 0, mayShowUserSettingsDialog: false }, success, error),
  }, setSnapshot), []);
  useFocusEffect(useCallback(() => () => controller.cancel(), [controller]));
  useEffect(() => {
    const handle = AppState.addEventListener('change', state => { if (state === 'background') controller.cancel(); });
    return () => { handle.remove(); controller.cancel(false); };
  }, [controller]);
  return { ...snapshot, busy: snapshot.phase === 'requesting' || snapshot.phase === 'finding', request: controller.request, cancel: controller.cancel, reset: controller.reset };
}
