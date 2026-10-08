// Small shared primitives: text with the right script font, buttons, banners, risk badge.
import type { ReactNode } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
  type StyleProp,
  type TextStyle,
  type ViewStyle,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ApiError, MOCK } from '../api/client';
import type { Lang, Mode, RiskLevel } from '../api/types';
import { useSession } from '../lib/session';
import { C, RISK, SIZE, fontFor } from '../lib/theme';

export function T({
  children,
  style,
  bold,
  size = SIZE.base,
  color = C.text,
  forLang,
}: {
  forLang?: Lang;
  children: ReactNode;
  style?: StyleProp<TextStyle>;
  bold?: boolean;
  size?: number;
  color?: string;
}) {
  const { lang } = useSession();
  const fontFamily = fontFor(forLang ?? lang, bold);
  return (
    <Text
      style={[
        { fontSize: size, color, lineHeight: Math.round(size * 1.45) },
        bold && !fontFamily ? { fontWeight: '700' } : null,
        fontFamily ? { fontFamily } : null,
        style,
      ]}
    >
      {children}
    </Text>
  );
}

export function Btn({
  label,
  onPress,
  kind = 'primary',
  disabled,
  style,
  forLang,
}: {
  forLang?: Lang;
  label: string;
  onPress: () => void;
  kind?: 'primary' | 'secondary';
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
}) {
  const primary = kind === 'primary';
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      onPress={onPress}
      disabled={disabled}
      style={({ pressed }) => [
        s.btn,
        primary ? s.btnPrimary : s.btnSecondary,
        (pressed || disabled) && { opacity: 0.6 },
        style,
      ]}
    >
      <T
        forLang={forLang}
        bold
        size={SIZE.large}
        color={primary ? C.primaryText : C.primary}
        style={{ textAlign: 'center' }}
      >
        {label}
      </T>
    </Pressable>
  );
}

export function Chip({
  label,
  selected,
  highlight,
  onPress,
}: {
  label: string;
  selected?: boolean;
  highlight?: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected }}
      onPress={onPress}
      style={[s.chip, selected && s.chipSelected, highlight && s.chipHighlight]}
    >
      <T bold={selected} color={selected ? C.primaryText : C.text}>
        {label}
      </T>
    </Pressable>
  );
}

export function Banner({ text, kind }: { text: string; kind: 'warn' | 'error' | 'info' | 'fixture' }) {
  const bg = { warn: C.warnBg, error: C.errorBg, info: C.infoBg, fixture: C.fixtureBg }[kind];
  const fg = kind === 'warn' ? C.warnText : C.infoText;
  return (
    <View style={[s.banner, { backgroundColor: bg }]} accessibilityRole="alert">
      <T bold color={fg}>
        {text}
      </T>
    </View>
  );
}

/** Banners every data screen shares: fixture, replay, stale, demo loads. */
export function DataBanners({
  fixture,
  replayDate,
  stale,
  demoLoads,
}: {
  fixture?: boolean;
  replayDate?: string | null;
  stale?: boolean;
  demoLoads?: boolean;
}) {
  const { t } = useSession();
  return (
    <>
      {(fixture || MOCK) && <Banner kind="fixture" text={t('fixture_banner')} />}
      {replayDate ? <Banner kind="info" text={t('replaying', { date: replayDate })} /> : null}
      {stale ? <Banner kind="warn" text={t('stale')} /> : null}
      {demoLoads ? <Banner kind="info" text={t('demo_loads')} /> : null}
    </>
  );
}

/** Risk is always colour + word + icon (Section 14.6). */
export function RiskBadge({ level }: { level: RiskLevel | null | undefined }) {
  const { t } = useSession();
  const r = RISK[level ?? 'none'];
  const word = level ? t(`risk_${level}`) : t('risk_not_reported');
  return (
    <View style={[s.badge, { backgroundColor: r.bg }]} accessible accessibilityLabel={word}>
      <T bold color={r.fg} size={SIZE.large}>
        {r.icon}
      </T>
      <T bold color={r.fg}>
        {word}
      </T>
    </View>
  );
}

export function Screen({ children }: { children: ReactNode }) {
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: C.bg }} edges={['bottom', 'left', 'right']}>
      <ScrollView contentContainerStyle={s.screen} keyboardShouldPersistTaps="handled">
        {children}
      </ScrollView>
    </SafeAreaView>
  );
}

export function Loading() {
  const { t } = useSession();
  return (
    <View style={s.loading}>
      <ActivityIndicator size="large" color={C.primary} />
      <T>{t('loading')}</T>
    </View>
  );
}

export function useErrorText() {
  const { t } = useSession();
  return (e: unknown): string => {
    if (e instanceof ApiError) {
      if (e.code === 'no_markets_in_radius') return t('err_no_markets');
      if (e.code === 'crop_not_configured') return t('err_crop_not_setup');
      if (e.code === 'origin_unknown') return t('err_origin_unknown');
      if (e.code === 'drive_time_unavailable') return t('err_drive_time');
      if (e.code === 'temperature_unavailable') return t('err_temperature');
      if (e.code === 'plan_not_found') return t('err_plan_not_found');
      if (e.code === 'bad_request' || e.status === 400) return t('err_bad_request');
      if (e.code === 'network') return t('err_network');
    }
    return t('err_generic');
  };
}

/** "same_day" mode must never show "days early" text. */
export const isPredictive = (mode: Mode | undefined) => mode === 'predictive';

export const s = StyleSheet.create({
  screen: { padding: 16, gap: 12, paddingBottom: 40 },
  btn: {
    minHeight: SIZE.touch,
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  btnPrimary: { backgroundColor: C.primary },
  btnSecondary: { backgroundColor: C.bg, borderWidth: 2, borderColor: C.primary },
  chip: {
    minHeight: SIZE.touch,
    paddingHorizontal: 14,
    justifyContent: 'center',
    borderRadius: 24,
    borderWidth: 2,
    borderColor: C.border,
    backgroundColor: C.bg,
  },
  chipSelected: { backgroundColor: C.primary, borderColor: C.primary },
  chipHighlight: { borderColor: C.highlightBorder, borderWidth: 3, backgroundColor: C.highlight },
  banner: { padding: 12, borderRadius: 8 },
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
    alignSelf: 'flex-start',
  },
  loading: { padding: 32, alignItems: 'center', gap: 12 },
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  card: { backgroundColor: C.card, borderRadius: 12, padding: 16, gap: 8, borderWidth: 1, borderColor: C.border },
});
