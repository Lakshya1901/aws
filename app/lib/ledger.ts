// Lifetime record on this phone (no user accounts, CLAUDE.md Section 21): every load or unsold lot the user
// confirms with "Use this", for the "Since you started" dashboard. Figures are the API's own (estimates, ranges).
import AsyncStorage from '@react-native-async-storage/async-storage';
import { getDataMode } from '../api/client';
import type { Impact, OutletOption, Range } from '../api/types';

// Live and demo totals are kept apart (D37): demo mode fills its own ledger with the demo day.
const key = () => (getDataMode() === 'demo' ? 'annasetu.ledger.demo.v1' : 'annasetu.ledger.v1');

export interface LedgerEntry {
  key: string; // plan_id|load: the same load chosen again replaces its entry
  at: string; // ISO time
  kind: 'farm' | 'rescue';
  qty_kg: number;
  prevented_kg: Range | null; // waste avoided; null when the user overrode the recommendation (not computed)
  rescued_kg: number;
  recovered_kg: number;
  // Extra Rs AnnaSetu made for the whole load: the API's money_saved_rs for the recommended outlet (farm), net at
  // an overriding outlet minus net at the nearest mandi, or the chosen outlet's net, since unsold stock would
  // otherwise be dumped (rescue); null = not yet estimated.
  extra_rs: Range | null;
}

export interface LedgerTotals {
  since: string | null;
  count: number;
  handled_kg: number;
  kept_kg: Range; // prevented + rescued + recovered (Section 9 Step 6)
  prevented_kg: Range;
  rescued_kg: number;
  recovered_kg: number;
  extra_rs: Range | null; // null when no entry has an estimate
}

export async function readLedger(): Promise<LedgerEntry[]> {
  try {
    const raw = await AsyncStorage.getItem(key());
    return raw ? (JSON.parse(raw) as LedgerEntry[]) : [];
  } catch {
    return [];
  }
}

export async function recordLedger(e: LedgerEntry): Promise<void> {
  const all = (await readLedger()).filter((x) => x.key !== e.key);
  all.push(e);
  try {
    await AsyncStorage.setItem(key(), JSON.stringify(all));
  } catch {}
}

/** Settings, "Clear saved data": forget every confirmed load and unsold lot of the current mode on this phone. */
export async function clearLedger(): Promise<void> {
  try {
    await AsyncStorage.removeItem(key());
  } catch {}
}

const add = (a: Range, b: Range): Range => ({ low: a.low + b.low, mid: a.mid + b.mid, high: a.high + b.high });
const ZERO: Range = { low: 0, mid: 0, high: 0 };
const pos = (r: Range): Range => ({ low: Math.max(0, r.low), mid: Math.max(0, r.mid), high: Math.max(0, r.high) });

/**
 * Lifetime totals. With today's plan (GET /impact), its figures replace this plan's confirmed entries for kg, so
 * unsold lots logged in the plan count too, without counting a load twice; money stays from confirmed entries
 * (the plan total has none). Unsold lots not confirmed add their routed kg to the kg sent through the app.
 */
export function totals(all: LedgerEntry[], plan: { id: string; impact: Impact } | null = null): LedgerTotals {
  const inPlan = (e: LedgerEntry) => plan !== null && e.key.startsWith(`${plan.id}|`);
  const entries = all.filter((e) => !inPlan(e));
  let prevented = ZERO;
  let extra_rs: Range | null = null;
  let rescued = 0;
  let recovered = 0;
  for (const e of entries) {
    // Only what AnnaSetu gained counts (D35): a load with no waste avoided, or that earned less than the nearest
    // mandi, adds 0 and never cancels another load's gain.
    if (e.prevented_kg) prevented = add(prevented, pos(e.prevented_kg));
    // Entries saved before this field count nothing.
    if (e.extra_rs) extra_rs = add(extra_rs ?? ZERO, pos(e.extra_rs));
    rescued += e.rescued_kg;
    recovered += e.recovered_kg;
  }
  let handled = entries.reduce((s, e) => s + e.qty_kg, 0);
  if (plan) {
    const mine = all.filter(inPlan);
    for (const e of mine) if (e.extra_rs) extra_rs = add(extra_rs ?? ZERO, pos(e.extra_rs));
    const i = plan.impact;
    if (i.waste_avoided_kg) prevented = add(prevented, pos(i.waste_avoided_kg));
    rescued += i.rescued_kg;
    recovered += i.recovered_kg;
    const routedMine = mine.filter((e) => e.kind === 'rescue').reduce((s, e) => s + e.rescued_kg + e.recovered_kg, 0);
    handled += mine.reduce((s, e) => s + e.qty_kg, 0) + Math.max(0, i.rescued_kg + i.recovered_kg - routedMine);
  }
  const extra = rescued + recovered;
  return {
    since: all.length ? all.map((e) => e.at).sort()[0] : null,
    count: all.length,
    handled_kg: handled,
    kept_kg: { low: prevented.low + extra, mid: prevented.mid + extra, high: prevented.high + extra },
    prevented_kg: prevented,
    rescued_kg: rescued,
    recovered_kg: recovered,
    extra_rs,
  };
}

/** Net Rs for the whole quantity at an outlet (range x kg), or null when its net value is not estimated. */
export function earnFor(o: OutletOption, qtyKg: number): Range | null {
  const n = o.net_rs_per_kg;
  return n ? { low: n.low * qtyKg, mid: n.mid * qtyKg, high: n.high * qtyKg } : null;
}

/** Extra Rs from choosing `chosen` over the nearest mandi `nearest` for the whole quantity, or null. */
export function extraOver(chosen: OutletOption, nearest: OutletOption, qtyKg: number): Range | null {
  const c = earnFor(chosen, qtyKg);
  const d = earnFor(nearest, qtyKg);
  if (!c || !d) return null;
  const v = [c.low - d.low, c.mid - d.mid, c.high - d.high];
  return { low: Math.min(...v), mid: v[1], high: Math.max(...v) };
}

/** Ledger lines from one API impact (a rescue lot has no prevented share). */
export function fromImpact(impact: Impact, kind: 'farm' | 'rescue') {
  return {
    prevented_kg: kind === 'farm' ? impact.waste_avoided_kg : null,
    rescued_kg: impact.rescued_kg,
    recovered_kg: impact.recovered_kg,
  };
}
