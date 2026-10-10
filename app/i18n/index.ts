// Reads the shared copy files in config/copy (resolved by Metro via metro.config.js watchFolders).
import en from '../../config/copy/en.json';
import hi from '../../config/copy/hi.json';
import bn from '../../config/copy/bn.json';
import mr from '../../config/copy/mr.json';
import te from '../../config/copy/te.json';
import ta from '../../config/copy/ta.json';
import gu from '../../config/copy/gu.json';
import ur from '../../config/copy/ur.json';
import kn from '../../config/copy/kn.json';
import or_ from '../../config/copy/or.json';
import ml from '../../config/copy/ml.json';
import pa from '../../config/copy/pa.json';
import as_ from '../../config/copy/as.json';
import mai from '../../config/copy/mai.json';
import sat from '../../config/copy/sat.json';
import ks from '../../config/copy/ks.json';
import ne from '../../config/copy/ne.json';
import sd from '../../config/copy/sd.json';
import doi from '../../config/copy/doi.json';
import kok from '../../config/copy/kok.json';
import mni from '../../config/copy/mni.json';
import type { Lang } from '../api/types';

export type CopyKey = Exclude<keyof typeof en, '_review'>;
type Copy = Record<string, unknown>;

const COPY: Record<Lang, Copy> = {
  en, hi, bn, mr, te, ta, gu, ur, kn, or: or_, ml, pa, as: as_, mai, sat, ks, ne, sd, doi, kok, mni,
};

/**
 * English plus India's 20 most spoken languages (Census 2011), in that order. name = the language's own name.
 * voice = Amazon Transcribe batch supports it (voice input); spoken replies stay Hindi and Indian English (Polly).
 * Every language other than English, Hindi and Kannada is machine-drafted and pending native review (CLAUDE.md D27).
 */
export const LANG_INFO: Record<Lang, { name: string; english: string; script: Script; voice: boolean }> = {
  en: { name: 'English', english: 'English', script: 'latn', voice: true },
  hi: { name: 'हिन्दी', english: 'Hindi', script: 'deva', voice: true },
  bn: { name: 'বাংলা', english: 'Bengali', script: 'beng', voice: true },
  mr: { name: 'मराठी', english: 'Marathi', script: 'deva', voice: true },
  te: { name: 'తెలుగు', english: 'Telugu', script: 'telu', voice: true },
  ta: { name: 'தமிழ்', english: 'Tamil', script: 'taml', voice: true },
  gu: { name: 'ગુજરાતી', english: 'Gujarati', script: 'gujr', voice: true },
  ur: { name: 'اردو', english: 'Urdu', script: 'arab', voice: false },
  kn: { name: 'ಕನ್ನಡ', english: 'Kannada', script: 'knda', voice: true },
  or: { name: 'ଓଡ଼ିଆ', english: 'Odia', script: 'orya', voice: true },
  ml: { name: 'മലയാളം', english: 'Malayalam', script: 'mlym', voice: true },
  pa: { name: 'ਪੰਜਾਬੀ', english: 'Punjabi', script: 'guru', voice: true },
  as: { name: 'অসমীয়া', english: 'Assamese', script: 'beng', voice: false },
  mai: { name: 'मैथिली', english: 'Maithili', script: 'deva', voice: false },
  sat: { name: 'ᱥᱟᱱᱛᱟᱲᱤ', english: 'Santali', script: 'olck', voice: false },
  ks: { name: 'کٲشُر', english: 'Kashmiri', script: 'arab', voice: false },
  ne: { name: 'नेपाली', english: 'Nepali', script: 'deva', voice: true },
  sd: { name: 'سنڌي', english: 'Sindhi', script: 'arab', voice: false },
  doi: { name: 'डोगरी', english: 'Dogri', script: 'deva', voice: false },
  kok: { name: 'कोंकणी', english: 'Konkani', script: 'deva', voice: false },
  mni: { name: 'মৈতৈলোন্', english: 'Manipuri', script: 'beng', voice: false },
};

export type Script = 'latn' | 'deva' | 'beng' | 'telu' | 'taml' | 'gujr' | 'arab' | 'knda' | 'orya' | 'mlym' | 'guru' | 'olck';

export const LANGS = Object.keys(LANG_INFO) as Lang[];

/** Perso-Arabic script languages read right to left. */
export const isRtl = (lang: Lang | null) => !!lang && LANG_INFO[lang].script === 'arab';

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
