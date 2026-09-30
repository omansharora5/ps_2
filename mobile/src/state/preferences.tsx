import AsyncStorage from '@react-native-async-storage/async-storage';
import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { AccessibilityInfo } from 'react-native';
import { LANGUAGES, isLanguageCode, t, type CopyKey, type LanguageCode } from '../../../shared/translations';

const STORAGE_KEY = 'vajra.language.v1';
type Preferences = {
  language: LanguageCode; locale: string; rtl: boolean; ready: boolean; reducedMotion: boolean;
  saved: boolean; storageError: boolean; setLanguage: (code: LanguageCode) => void;
  copy: (key: CopyKey) => string;
};
const Context = createContext<Preferences | null>(null);
export function PreferencesProvider({ children }: { children: ReactNode }) {
  const [language, setValue] = useState<LanguageCode>('en');
  const [ready, setReady] = useState(false);
  const [saved, setSaved] = useState(false);
  const [storageError, setError] = useState(false);
  const [reducedMotion, setReduced] = useState(false);
  const writeQueue = useRef(Promise.resolve());
  const selection = useRef(0);
  useEffect(() => {
    let active = true;
    AsyncStorage.getItem(STORAGE_KEY).then(value => { if (active && isLanguageCode(value)) setValue(value); }).catch(() => { if (active) setError(true); }).finally(() => { if (active) setReady(true); });
    AccessibilityInfo.isReduceMotionEnabled().then(value => { if (active) setReduced(value); }).catch(() => undefined);
    const subscription = AccessibilityInfo.addEventListener('reduceMotionChanged', setReduced);
    return () => { active = false; subscription.remove(); };
  }, []);
  const setLanguage = useCallback((code: LanguageCode) => {
    const token = ++selection.current;
    setValue(code); setSaved(false); setError(false);
    writeQueue.current = writeQueue.current.catch(() => undefined).then(() => AsyncStorage.setItem(STORAGE_KEY, code)).then(() => { if (token === selection.current) setSaved(true); }).catch(() => { if (token === selection.current) setError(true); });
  }, []);
  const details = LANGUAGES.find(item => item.code === language)!;
  return <Context.Provider value={{ language, locale: details.locale, rtl: details.rtl, ready, reducedMotion, saved, storageError, setLanguage, copy: key => t(language, key) }}>{children}</Context.Provider>;
}
export function usePreferences() {
  const context = useContext(Context);
  if (!context) throw new Error('Missing preferences provider');
  return context;
}
