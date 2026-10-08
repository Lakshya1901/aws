// Impact rows: waste avoided first, redirected separately. Null values read "not yet estimated", never zero.
import { View } from 'react-native';
import type { Impact } from '../api/types';
import { fmtNum } from '../i18n';
import { useSession } from '../lib/session';
import { C, SIZE } from '../lib/theme';
import { T, s } from './ui';

export function ImpactRows({ impact }: { impact: Impact }) {
  const { t } = useSession();
  const est = ` (${t('estimate')})`;
  const w = impact.waste_avoided_kg;
  const val = (v: number | null, key: 'kg_value' | 'km_value' | 'litres_value', decimals = 0, estimate = true) =>
    v == null ? t('not_estimated') : `${t(key, { v: fmtNum(v, decimals) })}${estimate ? est : ''}`;

  // Waste avoided first, redirected separately (never merged).
  const rows: [string, string, string?][] = [
    [
      t('waste_avoided'),
      w ? t('waste_value', { mid: fmtNum(w.mid) }) : t('not_estimated'),
      w ? `${t('waste_range', { low: fmtNum(w.low), high: fmtNum(w.high) })}${est}` : undefined,
    ],
    [t('redirected'), val(impact.redirected_kg, 'kg_value', 0, false)],
    [t('extra_km'), val(impact.extra_km, 'km_value')],
    [t('diesel'), val(impact.diesel_l, 'litres_value', 1)],
    [t('co2'), val(impact.co2_kg, 'kg_value', 1)],
    [t('water'), val(impact.water_l, 'litres_value')],
  ];
  return (
    <View style={[s.card, { gap: 6 }]}>
      {rows.map(([label, value, sub]) => (
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
