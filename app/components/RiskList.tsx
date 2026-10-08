import { View } from 'react-native';
import type { Mode, RiskMarket } from '../api/types';
import { fmtNum, fmtRs } from '../i18n';
import { useSession } from '../lib/session';
import { C, SIZE } from '../lib/theme';
import { RiskBadge, T, isPredictive, s } from './ui';

export function RiskList({ markets, mode }: { markets: RiskMarket[]; mode: Mode }) {
  const { t } = useSession();
  return (
    <View style={{ gap: 10 }}>
      {markets.map((m) => {
        const reported = m.risk_level !== null;
        const leadText =
          isPredictive(mode) && m.lead_days !== null && m.lead_days > 0 && m.risk_level !== 'glut'
            ? t('glut_in_days', { days: m.lead_days })
            : null;
        return (
          <View key={m.market_id} style={s.card}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
              <T bold size={SIZE.large} style={{ flexShrink: 1 }}>
                {m.name}
              </T>
              <RiskBadge level={m.risk_level} />
            </View>
            {m.distance_km !== null && (
              <T color={C.muted}>
                {t('km_value', { v: fmtNum(m.distance_km) })}
                {m.distance_approx ? ` (${t('approx')})` : ''} · {m.state}
              </T>
            )}
            {reported && (
              <View style={s.row}>
                {m.arrival_ratio !== null && <T bold>{t('ratio_usual', { ratio: m.arrival_ratio.toFixed(1) })}</T>}
                {m.modal_price_rs_per_kg !== null && <T>{t('price_per_kg', { price: fmtRs(m.modal_price_rs_per_kg) })}</T>}
                {m.price_change_3d !== null && (
                  <T>
                    {t('change_3d', {
                      change: `${m.price_change_3d > 0 ? '+' : ''}${Math.round(m.price_change_3d * 100)}`,
                    })}
                  </T>
                )}
              </View>
            )}
            {leadText && <T bold>{leadText}</T>}
            {m.as_of_date && (
              <T color={m.stale ? C.text : C.muted} bold={m.stale}>
                {t('as_of', { date: m.as_of_date })}
                {m.stale ? ` · ${t('stale')}` : ''}
              </T>
            )}
          </View>
        );
      })}
    </View>
  );
}
