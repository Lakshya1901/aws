import type { Lang, RiskLevel } from '../api/types';

// High-contrast palette, readable in sunlight (Section 14.6).
export const C = {
  bg: '#FFFFFF',
  text: '#111111',
  muted: '#3D3D3D',
  border: '#8A8A8A',
  primary: '#0B5D1E',
  primaryText: '#FFFFFF',
  card: '#F4F6F4',
  warnBg: '#FFE45C',
  warnText: '#111111',
  errorBg: '#B00020',
  errorText: '#FFFFFF',
  infoBg: '#0D3B66',
  infoText: '#FFFFFF',
  highlight: '#FFF3B0',
  highlightBorder: '#B26A00',
  fixtureBg: '#6A1B9A',
};

export const RISK: Record<RiskLevel | 'none', { bg: string; fg: string; icon: string }> = {
  safe: { bg: '#1B7F3B', fg: '#FFFFFF', icon: '✓' },
  watch: { bg: '#F2B705', fg: '#111111', icon: '!' },
  glut: { bg: '#B00020', fg: '#FFFFFF', icon: '✕' },
  none: { bg: '#5F6368', fg: '#FFFFFF', icon: '?' },
};

export const SIZE = { base: 16, large: 20, title: 26, number: 24, touch: 48 };

export function fontFor(lang: Lang | null, bold = false): string | undefined {
  if (lang === 'hi') return bold ? 'NotoSansDevanagari_700Bold' : 'NotoSansDevanagari_400Regular';
  if (lang === 'kn') return bold ? 'NotoSansKannada_700Bold' : 'NotoSansKannada_400Regular';
  return undefined;
}
