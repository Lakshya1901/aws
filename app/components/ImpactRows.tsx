// Impact rows: headline kg kept out of landfill, then Prevented (waste avoided), Rescued, Recovered and biogas energy,
// then redirected separately (never added in). Null values read "not yet estimated", never zero.
// Negative waste avoided (the trip spoils more than it saves) is said plainly, never shown as "waste avoided".
import { View } from 'react-native';
import type { Impact, Range } from '../api/types';
import { fmtNum } from '../i18n';
import { useSession } from '../lib/session';
import { C, SIZE } from '../lib/theme';
import { ListRow, Surface, T } from './ui';

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

type RowDef = { label: string; value: string; sub?: string; muted?: boolean };

/** Range line for a kept-out-of-landfill style figure. */
function useRangeText() {
  const { t } = useSession();
  return (w: Range): string =>
    `${w.low < 0 ? t('waste_range_loss', { loss: fmtNum(-w.low), high: fmtNum(w.high) }) : t('waste_range', { low: fmtNum(w.low), high: fmtNum(w.high) })} (${t('estimate')})`;
}

/** Headline block for the Impact screen: kept out of landfill, range, note, and the Prevented / Rescued / Recovered bar. */
export function ImpactHeadline({ impact }: { impact: Impact }) {
  const { t } = useSession();
  const rangeText = useRangeText();
  const kept = impact.kept_out_of_landfill_kg;
  const parts = [
    { key: 'prevented' as const, n: Math.max(0, impact.waste_avoided_kg?.mid ?? 0) },
    { key: 'rescued' as const, n: Math.max(0, impact.rescued_kg) },
    { key: 'recovered' as const, n: Math.max(0, impact.recovered_kg) },
  ];
  const total = parts.reduce((a, p) => a + p.n, 0);
  return (
    <View style={{ gap: 4 }}>
      <T size={SIZE.small} color={C.muted}>
        {t('kept_out_of_landfill')}
      </T>
      <T bold size={36} color={kept ? C.primary : C.muted} style={{ lineHeight: 44 }}>
        {kept ? t('waste_value', { mid: fmtNum(kept.mid) }) : t('not_estimated')}
      </T>
      {kept ? <T size={SIZE.small}>{rangeText(kept)}</T> : null}
      <T style={{ marginTop: 4 }}>{t('kept_note')}</T>
      {kept && kept.mid > 0 && total > 0 ? (
        <View style={{ gap: 8, marginTop: 12 }}>
          <View style={{ height: 12, borderRadius: 6, backgroundColor: C.track, overflow: 'hidden', flexDirection: 'row' }}>
            {parts.map((p, i) =>
              p.n > 0 ? <View key={p.key} style={{ flex: p.n, backgroundColor: i === 0 ? C.primary : i === 1 ? C.tonal : C.outline }} /> : null,
            )}
          </View>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 8 }}>
            {parts.map((p) => (
              <T key={p.key} size={SIZE.label} color={p.n > 0 ? C.text : C.muted}>
                {`${t(p.key)} ${Math.round((p.n / total) * 100)}%`}
              </T>
            ))}
          </View>
        </View>
      ) : null}
    </View>
  );
}

/**
 * One Surface of label/value rows. lines: plan (waste avoided, redirected, extra distance, diesel),
 * from (Prevented, Rescued, Recovered, biogas), trip (redirected, extra, diesel, CO2, water),
 * rescue (Rescued, Recovered, biogas energy).
 */
export function ImpactRows({ impact, lines }: { impact: Impact; lines: 'plan' | 'from' | 'trip' | 'rescue' }) {
  const { t } = useSession();
  const wasteText = useWasteText();
  const est = ` (${t('estimate')})`;
  const val = (v: number | null, key: 'kg_value' | 'km_value' | 'litres_value', decimals = 0, estimate = true) =>
    v == null ? t('not_estimated') : `${t(key, { v: fmtNum(v, decimals) })}${estimate ? est : ''}`;
  const waste = wasteText(impact.waste_avoided_kg, 'total');
  const energy =
    impact.biogas_energy == null
      ? t('not_estimated')
      : `${fmtNum(impact.biogas_energy, 1)} ${impact.biogas_energy_unit ?? ''}`.trim() + est;
  const water =
    impact.water_l != null && impact.water_l < 0
      ? `${t('water_lost', { v: fmtNum(-impact.water_l) })}${est}`
      : val(impact.water_l, 'litres_value');

  const R: Record<string, RowDef> = {
    waste: { label: t('waste_avoided'), value: waste.value, sub: waste.sub },
    prevented: { label: t('prevented'), value: waste.value, sub: waste.sub },
    rescued: { label: t('rescued'), value: val(impact.rescued_kg, 'kg_value') },
    recovered: { label: t('recovered'), value: val(impact.recovered_kg, 'kg_value') },
    biogas: { label: t('biogas_energy'), value: energy, muted: impact.biogas_energy == null },
    redirected: { label: t('redirected'), value: val(impact.redirected_kg, 'kg_value', 0, false) },
    redirectedNote: { label: t('redirected'), value: val(impact.redirected_kg, 'kg_value', 0, false), sub: t('redirected_note') },
    km: { label: t('extra_km'), value: val(impact.extra_km, 'km_value') },
    diesel: { label: t('diesel'), value: val(impact.diesel_l, 'litres_value', 1) },
    co2: { label: t('co2'), value: val(impact.co2_kg, 'kg_value', 1) },
    water: { label: t('water'), value: water },
  };
  const sets = {
    plan: ['waste', 'redirected', 'km', 'diesel'],
    from: ['prevented', 'rescued', 'recovered', 'biogas'],
    trip: ['redirectedNote', 'km', 'diesel', 'co2', 'water'],
    rescue: ['rescued', 'recovered', 'biogas'],
  } as const;
  return (
    <Surface>
      {sets[lines].map((k, i) => {
        const r = R[k]!;
        const isNull = r.value === t('not_estimated');
        return (
          <ListRow key={k} first={i === 0} style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
            <View style={{ flexShrink: 1, flex: 1, gap: 2 }}>
              <T bold>{r.label}</T>
              {r.sub ? (
                <T size={SIZE.small} color={C.muted}>
                  {r.sub}
                </T>
              ) : null}
            </View>
            <View style={{ flexShrink: 1, maxWidth: '50%' }}>
              <T bold={!isNull} color={isNull || r.muted ? C.muted : C.text} style={{ textAlign: 'right' }}>
                {r.value}
              </T>
            </View>
          </ListRow>
        );
      })}
    </Surface>
  );
}
