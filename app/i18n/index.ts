// Reads the shared copy files in config/copy (resolved by Metro via metro.config.js watchFolders).
import en from '../../config/copy/en.json';
import hi from '../../config/copy/hi.json';
import kn from '../../config/copy/kn.json';
import type { Lang } from '../api/types';

export type CopyKey = Exclude<keyof typeof en, '_review'>;
type Copy = Record<string, unknown>;

const COPY: Record<Lang, Copy> = { en, hi, kn };

export const LANGS: Lang[] = ['en', 'hi', 'kn'];

export function translate(
  lang: Lang,
  key: CopyKey,
  vars?: Record<string, string | number>,
): string {
  const raw = COPY[lang][key] ?? COPY.en[key];
  let s = typeof raw === 'string' ? raw : key;
  if (vars) {
    for (const [k, v] of Object.entries(vars)) s = s.split(`{${k}}`).join(String(v));
  }
  return s;
}

/** Indian digit grouping (1,00,000), no Intl dependency. */
export function fmtNum(n: number, decimals = 0): string {
  const neg = n < 0;
  const fixed = Math.abs(n).toFixed(decimals);
  const [int, frac] = fixed.split('.');
  let grouped = int;
  if (int.length > 3) {
    const last3 = int.slice(-3);
    const rest = int.slice(0, -3).replace(/\B(?=(\d{2})+(?!\d))/g, ',');
    grouped = `${rest},${last3}`;
  }
  return `${neg ? '-' : ''}${grouped}${frac ? `.${frac}` : ''}`;
}

/** Rs per kg: whole rupees unless the value is small. */
export function fmtRs(n: number): string {
  return Math.abs(n) < 10 ? fmtNum(n, 1).replace(/\.0$/, '') : fmtNum(n);
}
