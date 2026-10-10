// Shared Material 3 primitives (canvas "AnnaSetu screens", Foundations board): text with the right script font,
// buttons, chips, banners, status line, risk badge, list surfaces, navigation bar.
import { router, usePathname } from 'expo-router';
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
import { isRtl } from '../i18n';
import { useSession } from '../lib/session';
import { C, RADIUS, RISK, SHADOW, SIZE, fontFor } from '../lib/theme';
import { Icon, type IconName } from './Icon';

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
  return (
    <Text
      style={[
        { fontSize: size, color, lineHeight: Math.round(size * 1.45), fontFamily: fontFor(forLang ?? lang, bold) },
        isRtl(forLang ?? lang) ? { writingDirection: 'rtl', textAlign: 'right' } : null,
        style,
      ]}
    >
      {children}
    </Text>
  );
}

/** primary = filled pill (one per screen); secondary = outlined; text = text button. */
export function Btn({
  label,
  onPress,
  kind = 'primary',
  icon,
  disabled,
  style,
  forLang,
}: {
  forLang?: Lang;
  label: string;
  onPress: () => void;
  kind?: 'primary' | 'secondary' | 'text';
  icon?: IconName;
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
}) {
  const fg = kind === 'primary' ? C.primaryText : C.primary;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled }}
      onPress={onPress}
      disabled={disabled}
      style={({ pressed }) => [
        s.btn,
        kind === 'primary' ? s.btnPrimary : kind === 'secondary' ? s.btnSecondary : s.btnText,
        (pressed || disabled) && { opacity: 0.6 },
        style,
      ]}
    >
      {icon ? <Icon name={icon} size={20} color={fg} /> : null}
      <T forLang={forLang} bold size={kind === 'primary' ? SIZE.section : SIZE.base} color={fg} style={{ textAlign: 'center' }}>
        {label}
      </T>
    </Pressable>
  );
}

/** Material filter chip: selected = tonal fill with a check. highlight = needs the user's attention. */
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
      {selected ? <Icon name="check" size={18} color={C.onTonal} strokeWidth={2.6} /> : null}
      <T bold={selected} color={selected ? C.onTonal : C.text}>
        {label}
      </T>
    </Pressable>
  );
}

const BANNER: Record<'warn' | 'error' | 'info' | 'fixture', { bg: string; fg: string; icon: IconName }> = {
  warn: { bg: C.warnBg, fg: C.warnText, icon: 'warning' },
  error: { bg: C.errorBg, fg: C.errorText, icon: 'warning' },
  info: { bg: C.tonal, fg: C.onTonal, icon: 'alert' },
  fixture: { bg: C.fixtureBg, fg: '#FFFFFF', icon: 'alert' },
};

export function Banner({ text, kind }: { text: string; kind: 'warn' | 'error' | 'info' | 'fixture' }) {
  const b = BANNER[kind];
  return (
    <View style={[s.banner, { backgroundColor: b.bg }]} accessibilityRole="alert">
      <Icon name={b.icon} size={20} color={b.fg} strokeWidth={2.2} />
      <T bold color={b.fg} style={{ flexShrink: 1 }}>
        {text}
      </T>
    </View>
  );
}

/** One line per screen instead of "(estimate)" on every figure (D32): ranges stay, the label moves here. */
export function EstNote() {
  const { t } = useSession();
  return (
    <T size={SIZE.label} color={C.muted}>
      {t('est_note')}
    </T>
  );
}

/** Neutral pill for data labels: Demo loads, Demo stock, estimate. dashed = Not yet partnered. */
export function Tag({ text, dashed }: { text: string; dashed?: boolean }) {
  return (
    <View style={[s.tag, dashed && { borderStyle: 'dashed', borderColor: C.outline, backgroundColor: 'transparent' }]}>
      <T size={SIZE.label} color={C.text}>
        {text}
      </T>
    </View>
  );
}

/**
 * Data status every data screen shares: fixture, replay date, demo loads, stale.
 * Replay is a quiet line; stale is a warning (old data is never styled as current).
 */
export function DataBanners({
  fixture,
  replayDate,
  stale,
  demoLoads,
  demoLabel,
}: {
  fixture?: boolean;
  replayDate?: string | null;
  stale?: boolean;
  demoLoads?: boolean;
  demoLabel?: string;
}) {
  const { t } = useSession();
  return (
    <>
      {(fixture || MOCK) && <Banner kind="fixture" text={t('fixture_banner')} />}
      {replayDate || demoLoads ? (
        <View style={[s.row, { alignItems: 'center' }]}>
          {replayDate ? (
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
              <Icon name="history" size={16} color={C.muted} />
              <T size={SIZE.label} color={C.muted}>
                {t('replaying', { date: fmtDate(replayDate) })}
              </T>
            </View>
          ) : null}
          {demoLoads ? <Tag text={demoLabel ?? t('demo_loads')} /> : null}
        </View>
      ) : null}
      {stale ? <Banner kind="warn" text={t('stale')} /> : null}
    </>
  );
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
/** 2023-09-29 -> 29 Sep 2023 (plain date, no locale dependency). */
export function fmtDate(iso: string): string {
  const [y, m, d] = iso.split('-');
  const mi = Number(m) - 1;
  return y && d && MONTHS[mi] ? `${Number(d)} ${MONTHS[mi]} ${y}` : iso;
}

/** Risk is always colour + word + icon (Section 14.6). */
export function RiskBadge({ level }: { level: RiskLevel | null | undefined }) {
  const { t } = useSession();
  const r = RISK[level ?? 'none'];
  const word = level ? t(`risk_${level}`) : t('risk_not_reported');
  return (
    <View style={[s.badge, { backgroundColor: r.bg }]} accessible accessibilityLabel={word}>
      <Icon name={r.icon} size={16} color={r.fg} strokeWidth={2.8} />
      <T bold size={SIZE.label} color={r.fg}>
        {word}
      </T>
    </View>
  );
}

/** Round status icon for list rows; the word sits in the row text. */
export function RiskDot({ level }: { level: RiskLevel | null | undefined }) {
  const r = RISK[level ?? 'none'];
  return (
    <View style={[s.dot, { backgroundColor: r.bg }]}>
      <Icon name={r.icon} size={20} color={r.fg} strokeWidth={2.8} />
    </View>
  );
}

/** White surface on the beige page: one list or one decision unit. Never nest. */
export function Surface({ children, style }: { children: ReactNode; style?: StyleProp<ViewStyle> }) {
  return <View style={[s.surface, style]}>{children}</View>;
}

/** List row inside a Surface; divider above every row but the first. */
export function ListRow({ children, first, style }: { children: ReactNode; first?: boolean; style?: StyleProp<ViewStyle> }) {
  return <View style={[s.listRow, !first && s.divider, style]}>{children}</View>;
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return (
    <T bold size={SIZE.section} style={{ marginTop: 4 }}>
      {children}
    </T>
  );
}

export function Screen({ children, nav }: { children: ReactNode; nav?: boolean }) {
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: C.bg }} edges={nav ? ['left', 'right'] : ['bottom', 'left', 'right']}>
      <ScrollView contentContainerStyle={s.screen} keyboardShouldPersistTaps="handled">
        {children}
      </ScrollView>
      {nav ? <NavBar /> : null}
    </SafeAreaView>
  );
}

const TABS: { path: '/today' | '/plan' | '/impact'; icon: IconName; key: 'today_title' | 'todays_plan' | 'impact' }[] = [
  { path: '/today', icon: 'home', key: 'today_title' },
  { path: '/plan', icon: 'truck', key: 'todays_plan' },
  { path: '/impact', icon: 'chart', key: 'impact' },
];

/** Material navigation bar: Today, Today's plan, Impact. */
export function NavBar() {
  const { t } = useSession();
  const path = usePathname();
  return (
    <SafeAreaView edges={['bottom']} style={{ backgroundColor: C.surfaceLow }}>
      <View style={s.nav} accessibilityRole="tablist">
        {TABS.map((tab) => {
          const active = path === tab.path;
          return (
            <Pressable
              key={tab.path}
              accessibilityRole="tab"
              accessibilityState={{ selected: active }}
              accessibilityLabel={t(tab.key)}
              onPress={() => !active && router.replace(tab.path)}
              style={s.navItem}
            >
              <View style={[s.navPill, active && { backgroundColor: C.tonal }]}>
                <Icon name={tab.icon} size={22} color={active ? C.onTonal : C.muted} strokeWidth={active ? 2.2 : 2} />
              </View>
              <T bold={active} size={SIZE.label} color={active ? C.text : C.muted}>
                {t(tab.key)}
              </T>
            </Pressable>
          );
        })}
      </View>
    </SafeAreaView>
  );
}

export function Loading() {
  const { t } = useSession();
  return (
    <View style={s.loading}>
      <ActivityIndicator size="large" color={C.primary} />
      <T color={C.muted}>{t('loading')}</T>
    </View>
  );
}

export function useErrorText() {
  const { t } = useSession();
  return (e: unknown): string => {
    if (e instanceof ApiError) {
      if (e.code === 'no_markets_in_radius') return t('err_no_markets');
      if (e.code === 'crop_not_configured') return t('err_crop_not_setup');
      if (e.code === 'origin_unknown' || e.code === 'origin_required') return t('err_origin_unknown');
      if (e.code === 'drive_time_unavailable') return t('err_drive_time');
      if (e.code === 'temperature_unavailable') return t('err_temperature');
      if (e.code === 'split_required') return t('err_split_required');
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
  screen: { padding: 16, gap: 16, paddingBottom: 32 },
  btn: {
    minHeight: SIZE.touch,
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 24,
    flexDirection: 'row',
    gap: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  btnPrimary: { backgroundColor: C.primary, minHeight: 56, borderRadius: RADIUS.pill },
  btnSecondary: { backgroundColor: 'transparent', borderWidth: 1, borderColor: C.outline },
  btnText: { backgroundColor: 'transparent', paddingHorizontal: 12 },
  chip: {
    minHeight: SIZE.touch,
    paddingHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    borderRadius: RADIUS.chip,
    borderWidth: 1,
    borderColor: C.outline,
    backgroundColor: 'transparent',
  },
  chipSelected: { backgroundColor: C.tonal, borderColor: C.tonal, paddingLeft: 10 },
  chipHighlight: { borderColor: C.warnText, borderWidth: 2, backgroundColor: C.warnBg },
  banner: { padding: 12, borderRadius: RADIUS.field, flexDirection: 'row', gap: 10, alignItems: 'flex-start' },
  tag: { paddingHorizontal: 10, paddingVertical: 2, borderRadius: 999, backgroundColor: C.chip, borderWidth: 1, borderColor: C.chip },
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: RADIUS.chip,
    alignSelf: 'flex-start',
  },
  dot: { width: 36, height: 36, borderRadius: 18, alignItems: 'center', justifyContent: 'center' },
  surface: { backgroundColor: C.surface, borderRadius: RADIUS.surface, ...SHADOW },
  listRow: { paddingHorizontal: 16, paddingVertical: 14, minHeight: 56, gap: 4 },
  divider: { borderTopWidth: 1, borderTopColor: C.divider },
  nav: { flexDirection: 'row', paddingTop: 12, paddingBottom: 12 },
  navItem: { flex: 1, alignItems: 'center', gap: 4, minHeight: SIZE.touch },
  navPill: { width: 64, height: 32, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  loading: { padding: 32, alignItems: 'center', gap: 12 },
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  card: { backgroundColor: C.surface, borderRadius: RADIUS.surface, padding: 16, gap: 8, ...SHADOW },
});
