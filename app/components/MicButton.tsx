// Hold-to-speak mic: press in starts an m4a recording, release stops it and hands back the file URI.
import {
  RecordingPresets,
  requestRecordingPermissionsAsync,
  setAudioModeAsync,
  useAudioRecorder,
} from 'expo-audio';
import { useEffect, useRef, useState } from 'react';
import { Pressable, View } from 'react-native';
import { useSession } from '../lib/session';
import { C, SIZE } from '../lib/theme';
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

  useEffect(() => () => {
    if (timer.current) clearTimeout(timer.current);
  }, []);

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
    <View style={{ alignItems: 'center', gap: 10, paddingVertical: 8 }}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={t('speak')}
        disabled={disabled}
        onPressIn={() => void start()}
        onPressOut={() => void stop()}
        style={{
          width: 140,
          height: 140,
          borderRadius: 70,
          backgroundColor: recording ? C.errorBg : C.primary,
          justifyContent: 'center',
          alignItems: 'center',
          opacity: disabled ? 0.5 : 1,
          borderWidth: 6,
          borderColor: recording ? C.warnBg : C.card,
        }}
      >
        <T bold size={44} color={C.primaryText}>
          {'🎤'}
        </T>
      </Pressable>
      <T bold size={SIZE.large}>
        {recording ? t('recording') : t('speak')}
      </T>
    </View>
  );
}
