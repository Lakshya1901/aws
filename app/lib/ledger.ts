// Lifetime record on this phone (no user accounts, CLAUDE.md Section 21): every load or unsold lot the user
// confirms with "Use this", for the "Since you started" dashboard. Figures are the API's own (estimates, ranges).
import AsyncStorage from '@react-native-async-storage/async-storage';
import type { Impact, OutletOption, Range } from '../api/types';

const KEY = 'annasetu.ledger.v1';

export interface LedgerEntry {
  key: string; // plan_id|load: the same load chosen again replaces its entry
  at: string; // ISO time
  kind: 'farm' | 'rescue';
  qty_kg: number;
  prevented_kg: Range | null; // waste avoided; null when the user overrode the recommendation (not computed)
  rescued_kg: number;
  recovered_kg: number;
  earn_rs: Range | null; // net Rs for the whole load at the chosen outlet; null = not yet estimated
}

export interface LedgerTotals {
  since: string | null;
  count: number;
  handled_kg: number;
  kept_kg: Range; // prevented + rescued + recovered (Section 9 Step 6)
  prevented_kg: Range;
  rescued_kg: number;
  recovered_kg: number;
  earn_rs: Range | null; // null when no entry has an estimate
}

export async function readLedger(): Promise<LedgerEntry[]> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as LedgerEntry[]) : [];
  } catch {
    return [];
  }
}

export async function recordLedger(e: LedgerEntry): Promise<void> {
  const all = (await readLedger()).filter((x) => x.key !== e.key);
  all.push(e);
  try {
    await AsyncStorage.setItem(KEY, JSON.stringify(all));
  } catch {}
}

const add = (a: Range, b: Range): Range => ({ low: a.low + b.low, mid: a.mid + b.mid, high: a.high + b.high });
const ZERO: Range = { low: 0, mid: 0, high: 0 };

export function totals(entries: LedgerEntry[]): LedgerTotals {
  let prevented = ZERO;
  let earn: Range | null = null;
  let rescued = 0;
  let recovered = 0;
  for (const e of entries) {
    if (e.prevented_kg) prevented = add(prevented, e.prevented_kg);
    if (e.earn_rs) earn = add(earn ?? ZERO, e.earn_rs);
    rescued += e.rescued_kg;
    recovered += e.recovered_kg;
  }
  const extra = rescued + recovered;
  return {
    since: entries.length ? entries.map((e) => e.at).sort()[0] : null,
    count: entries.length,
    handled_kg: entries.reduce((s, e) => s + e.qty_kg, 0),
    kept_kg: { low: prevented.low + extra, mid: prevented.mid + extra, high: prevented.high + extra },
    prevented_kg: prevented,
    rescued_kg: rescued,
    recovered_kg: recovered,
    earn_rs: earn,
  };
}

/** Net Rs for the whole quantity at an outlet (range x kg), or null when its net value is not estimated. */
export function earnFor(o: OutletOption, qtyKg: number): Range | null {
  const n = o.net_rs_per_kg;
  return n ? { low: n.low * qtyKg, mid: n.mid * qtyKg, high: n.high * qtyKg } : null;
}

/** Ledger lines from one API impact (a rescue lot has no prevented share). */
export function fromImpact(impact: Impact, kind: 'farm' | 'rescue') {
  return {
    prevented_kg: kind === 'farm' ? impact.waste_avoided_kg : null,
    rescued_kg: impact.rescued_kg,
    recovered_kg: impact.recovered_kg,
  };
}
