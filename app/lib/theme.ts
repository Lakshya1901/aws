import type { Lang, RiskLevel } from '../api/types';
import type { IconName } from '../components/Icon';

// Material 3 palette on a light beige page, readable in sunlight (Section 14.6; canvas "AnnaSetu screens").
export const C = {
  bg: '#FAF6EE', // page
  surface: '#FFFFFF', // lists and cards
  surfaceLow: '#F2ECE0', // navigation bar, quote blocks
  chip: '#EFE9DD', // neutral chips and badges
  track: '#F1EBDF', // empty part of bars
  divider: '#EEE8DC',
  outline: '#8D9A90', // outlined buttons, unselected chips, text fields
  text: '#24352A',
  muted: '#5D6A60',
  primary: '#215C3B',
  primaryText: '#FFFFFF',
  tonal: '#CFE3D4', // selected chip, active navigation item
  onTonal: '#12351F',
  amber: '#E9A23B', // Watch fill, dark text only
  warnBg: '#FBF0DC', // old data, reasons, highlighted fields
  warnText: '#7A4E0E',
  red: '#B94337', // Glut only
  errorBg: '#B94337',
  errorText: '#FFFFFF',
  fixtureBg: '#6A1B9A',
  // Legacy names kept for screens not yet restyled.
  card: '#FFFFFF',
  border: '#8D9A90',
  highlight: '#FBF0DC',
  highlightBorder: '#7A4E0E',
  infoBg: '#CFE3D4',
  infoText: '#12351F',
};

/** One soft elevation for white surfaces on the beige page (Material 3 level 1). */
export const SHADOW = {
  shadowColor: '#3C301E',
  shadowOpacity: 0.08,
  shadowRadius: 6,
  shadowOffset: { width: 0, height: 2 },
  elevation: 1,
} as const;

/** Risk is always colour + word + icon (Section 14.6). */
export const RISK: Record<RiskLevel | 'none', { bg: string; fg: string; icon: IconName; word: string }> = {
  safe: { bg: '#215C3B', fg: '#FFFFFF', icon: 'check', word: '#215C3B' },
  watch: { bg: '#E9A23B', fg: '#24352A', icon: 'alert', word: '#7A4E0E' },
  glut: { bg: '#B94337', fg: '#FFFFFF', icon: 'x', word: '#B94337' },
  none: { bg: '#EFE9DD', fg: '#24352A', icon: 'dash', word: '#5D6A60' },
};

// Material 3 type roles: headline 28, title 20, section 18, body 16, secondary 15, label 14.
export const SIZE = { label: 14, small: 15, base: 16, section: 18, large: 20, number: 24, title: 28, touch: 48 };
export const RADIUS = { surface: 16, field: 12, chip: 8, pill: 28 };

export function fontFor(lang: Lang | null, bold = false): string {
  if (lang === 'hi') return bold ? 'NotoSansDevanagari_700Bold' : 'NotoSansDevanagari_400Regular';
  if (lang === 'kn') return bold ? 'NotoSansKannada_700Bold' : 'NotoSansKannada_400Regular';
  return bold ? 'NotoSans_600SemiBold' : 'NotoSans_400Regular';
}
