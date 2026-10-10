// Hold-to-speak mic: press in starts an m4a recording, release stops it and hands back the file URI.
import {
  RecordingPresets,
  requestRecordingPermissionsAsync,
  setAudioModeAsync,
  useAudioRecorder,
} from 'expo-audio';
import { useEffect, useRef, useState } from 'react';
import { Animated, Easing, Pressable, View } from 'react-native';
import { useSession } from '../lib/session';
import { C, SHADOW, SIZE } from '../lib/theme';
import { Icon } from './Icon';
import { T } from './ui';

const MAX_MS = 20000; // clips under 20 s (Section 14.4)
const MIN_MS = 600;

export function MicButton({
  disabled,
  onRecorded,
  onFailed,
}: {
  disabled?: boolean;
  onRecorded: (uri: string) => void;
  onFailed: (reason: 'denied' | 'error') => void;
}) {
  const { t } = useSession();
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const [recording, setRecording] = useState(false);
  const startedAt = useRef(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const active = useRef(false);
  const starting = useRef(false);
  const released = useRef(false);
  const pulse = useRef(new Animated.Value(0)).current;
  const [secs, setSecs] = useState(0);

  useEffect(() => () => {
    if (timer.current) clearTimeout(timer.current);
  }, []);

  // While recording: a pulsing ring and a seconds counter, so it is clear the phone is listening.
  useEffect(() => {
    if (!recording) {
      pulse.stopAnimation();
      pulse.setValue(0);
      setSecs(0);
      return;
    }
    const loop = Animated.loop(
      Animated.timing(pulse, { toValue: 1, duration: 1100, easing: Easing.out(Easing.ease), useNativeDriver: true }),
    );
    loop.start();
    const tick = setInterval(() => setSecs(Math.floor((Date.now() - startedAt.current) / 1000)), 250);
    return () => {
      loop.stop();
      clearInterval(tick);
    };
  }, [recording, pulse]);

  async function start() {
    if (disabled || starting.current || active.current) return;
    starting.current = true;
    released.current = false;
    try {
      const perm = await requestRecordingPermissionsAsync();
      if (!perm.granted) {
        onFailed('denied');
        return;
      }
      // Released while the permission prompt was open: wait for the next hold.
      if (released.current) return;
      await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
      await recorder.prepareToRecordAsync();
      if (released.current) return;
      recorder.record();
      active.current = true;
      startedAt.current = Date.now();
      setRecording(true);
      timer.current = setTimeout(() => void stop(), MAX_MS);
    } catch {
      setRecording(false);
      onFailed('error');
    } finally {
      starting.current = false;
    }
  }

  async function stop() {
    released.current = true;
    if (!active.current) return;
    active.current = false;
    if (timer.current) clearTimeout(timer.current);
    setRecording(false);
    try {
      await recorder.stop();
      await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true });
      const tooShort = Date.now() - startedAt.current < MIN_MS;
      if (!recorder.uri || tooShort) {
        onFailed('error');
        return;
      }
      onRecorded(recorder.uri);
    } catch {
      onFailed('error');
    }
  }

  return (
    <View style={{ alignItems: 'center', gap: 12, paddingVertical: 8 }}>
      <View
        style={{
          width: 144,
          height: 144,
          borderRadius: 72,
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: recording ? C.tonal : 'transparent',
        }}
      >
        {recording && (
          <Animated.View
            pointerEvents="none"
            style={{
              position: 'absolute',
              width: 144,
              height: 144,
              borderRadius: 72,
              backgroundColor: C.primary,
              opacity: pulse.interpolate({ inputRange: [0, 1], outputRange: [0.35, 0] }),
              transform: [{ scale: pulse.interpolate({ inputRange: [0, 1], outputRange: [0.85, 1.35] }) }],
            }}
          />
        )}
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={t('speak')}
          disabled={disabled}
          onPressIn={() => void start()}
          onPressOut={() => void stop()}
          style={{
            width: 120,
            height: 120,
            borderRadius: 60,
            backgroundColor: C.primary,
            justifyContent: 'center',
            alignItems: 'center',
            opacity: disabled ? 0.5 : 1,
            ...SHADOW,
          }}
        >
          <Icon name="mic" size={52} color={C.primaryText} strokeWidth={2} />
        </Pressable>
      </View>
      <T bold size={SIZE.large}>
        {recording ? `${t('recording')} 0:${String(secs).padStart(2, '0')}` : t('speak')}
      </T>
      {recording ? null : (
        <T size={SIZE.small} color={C.muted} style={{ textAlign: 'center' }}>
          {t('say_hint')}
        </T>
      )}
    </View>
  );
}
