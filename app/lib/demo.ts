// Demo mode's ready-made day at Azadpur, Delhi (D37): six farm loads and five unsold lots, run through the API on the
// replay day and saved as if each was confirmed with "Use this", so Today's plan and Impact are filled at once.
// Simulated loads, real prices and routes; the app shows "Demo loads". Quantities chosen by the team (October 11).
import { api, getDataMode } from '../api/client';
import type { CropId, Lang, Origin, PlanLoad } from '../api/types';
import { clearLedger, earnFor, fromImpact, recordLedger } from './ledger';

// Stop if the user leaves demo mode meanwhile: the ledger in use follows the mode.
const stillDemo = () => {
  if (getDataMode() !== 'demo') throw new Error('left demo mode');
};

const AZADPUR: Origin = { lat: null, lon: null, place: 'Azadpur' };
const FARM: [CropId, number][] = [
  ['banana', 5000], ['papaya', 5000], ['guava', 5000], ['pumpkin', 5000], ['capsicum', 5000], ['cabbage', 5000],
];
const UNSOLD: [CropId, number, number][] = [ // crop, kg, days since harvest
  ['onion', 3000, 3], ['tomato', 3000, 1], ['cabbage', 2000, 1], ['banana', 2000, 2], ['cauliflower', 1500, 1],
];

/** Replace the demo ledger with the demo day; returns the farm loads and plan id for Today's plan. */
export async function seedDemo(lang: Lang): Promise<{ loads: PlanLoad[]; planId: string }> {
  const draft: PlanLoad[] = FARM.map(([crop, kg], i) => ({
    load_id: `demo${i + 1}`, crop, quantity_kg: kg, origin: AZADPUR, harvest: 'today',
  }));
  const plan = await api.plan({ loads: draft, language: lang });
  stillDemo();
  await clearLedger();
  const at = new Date().toISOString();
  const loads = draft.map((l) => {
    const a = plan.allocations.find((x) => x.load_id === l.load_id)!;
    return { ...l, chosen_outlet_id: a.outlet.outlet_id, override: false };
  });
  for (const a of plan.allocations) {
    stillDemo();
    await recordLedger({
      key: `${plan.plan_id}|${a.load_id}`, at, kind: 'farm', qty_kg: a.quantity_kg,
      ...fromImpact(a.impact, 'farm'), extra_rs: a.impact.money_saved_rs ?? null,
    });
  }
  // One at a time: each lot is added to the same plan record.
  for (const [crop, kg, days] of UNSOLD) {
    const r = await api.rescue({
      source: 'mandi_unsold', crop, quantity_kg: kg, days_since_harvest: days, origin: AZADPUR, language: lang,
      plan_id: plan.plan_id,
    });
    const dest = r.top ?? r.recover;
    stillDemo();
    await recordLedger({
      key: `${r.plan_id}|rescue|${r.crop}|${r.quantity_kg}`, at, kind: 'rescue', qty_kg: r.quantity_kg,
      ...fromImpact(r.impact, 'rescue'), extra_rs: dest ? earnFor(dest, r.split.edible_kg) : null,
    });
  }
  return { loads, planId: plan.plan_id };
}
