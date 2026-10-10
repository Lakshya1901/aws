// Impact rows: headline kg kept out of landfill, then Prevented (waste avoided), Rescued, Recovered and biogas energy,
// then redirected separately (never added in). Null values read "not yet estimated", never zero.
// Negative waste avoided (the trip spoils more than it saves) is said plainly, never shown as "waste avoided".
import { View } from 'react-native';
import type { Impact, Range } from '../api/types';
import { fmtNum } from '../i18n';
import { useSession } from '../lib/session';
import { C, SIZE } from '../lib/theme';
import { T, s } from './ui';

/** Waste avoided as {value, sub}: null -> not yet estimated; mid <= 0 -> "No waste avoided" (+ extra spoilage). */
export function useWasteText() {
  const { t } = useSession();
  const est = ` (${t('estimate')})`;
  return (w: Range | null, scope: 'load' | 'total'): { value: string; sub?: string } => {
    if (!w) return { value: t('not_estimated') };
    if (w.mid <= 0) {
      const none = t(scope === 'load' ? 'waste_none_load' : 'waste_none_total');
      const lost = Math.round(-w.mid);
      return lost > 0 ? { value: none, sub: `${t('waste_spoilage', { kg: fmtNum(lost) })}${est}` } : { value: none };
    }
    const sub =
      w.low < 0
        ? t('waste_range_loss', { loss: fmtNum(-w.low), high: fmtNum(w.high) })
        : t('waste_range', { low: fmtNum(w.low), high: fmtNum(w.high) });
    return { value: t('waste_value', { mid: fmtNum(w.mid) }), sub: `${sub}${est}` };
  };
}

/** lines "rescue": only the headline, Rescued, Recovered and biogas energy (one Rescue lot has nothing prevented). */
export function ImpactRows({ impact, lines = 'all' }: { impact: Impact; lines?: 'all' | 'rescue' }) {
  const { t } = useSession();
  const wasteText = useWasteText();
  const est = ` (${t('estimate')})`;
  const val = (v: number | null, key: 'kg_value' | 'km_value' | 'litres_value', decimals = 0, estimate = true) =>
    v == null ? t('not_estimated') : `${t(key, { v: fmtNum(v, decimals) })}${estimate ? est : ''}`;
  const waste = wasteText(impact.waste_avoided_kg, 'total');
  const kept = impact.kept_out_of_landfill_kg;
  const energy =
    impact.biogas_energy == null
      ? t('not_estimated')
      : `${fmtNum(impact.biogas_energy, 1)} ${impact.biogas_energy_unit ?? ''}`.trim() + est;
  const water =
    impact.water_l != null && impact.water_l < 0
      ? `${t('water_lost', { v: fmtNum(-impact.water_l) })}${est}`
      : val(impact.water_l, 'litres_value');

  // Kept out of landfill = Prevented + Rescued + Recovered; redirected separately (never merged).
  const rows: [string, string, string?][] = [
    [
      t('kept_out_of_landfill'),
      kept ? t('waste_value', { mid: fmtNum(kept.mid) }) : t('not_estimated'),
      kept ? `${t('waste_range', { low: fmtNum(kept.low), high: fmtNum(kept.high) })}${est}` : undefined,
    ],
    [`${t('prevented')}: ${t('waste_avoided')}`, waste.value, waste.sub],
    [t('rescued'), val(impact.rescued_kg, 'kg_value')],
    [t('recovered'), val(impact.recovered_kg, 'kg_value')],
    [t('biogas_energy'), energy],
    [t('redirected'), val(impact.redirected_kg, 'kg_value', 0, false)],
    [t('extra_km'), val(impact.extra_km, 'km_value')],
    [t('diesel'), val(impact.diesel_l, 'litres_value', 1)],
    [t('co2'), val(impact.co2_kg, 'kg_value', 1)],
    [t('water'), water],
  ];
  const shown = lines === 'rescue' ? rows.filter((_, i) => [0, 2, 3, 4].includes(i)) : rows;
  return (
    <View style={[s.card, { gap: 6 }]}>
      {shown.map(([label, value, sub]) => (
        <View key={label} style={{ paddingVertical: 4 }}>
          <T color={C.muted}>{label}</T>
          <T bold size={SIZE.number}>
            {value}
          </T>
          {sub ? <T>{sub}</T> : null}
        </View>
      ))}
    </View>
  );
}
