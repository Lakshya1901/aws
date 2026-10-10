import { useState } from 'react';
import { Pressable, View } from 'react-native';
import type { Mode, RiskMarket } from '../api/types';
import { fmtNum, fmtRs } from '../i18n';
import { useSession } from '../lib/session';
import { C, SIZE } from '../lib/theme';
import { Icon } from './Icon';
import { ListRow, RiskDot, Surface, T, isPredictive } from './ui';

export function RiskList({ markets, mode }: { markets: RiskMarket[]; mode: Mode }) {
  const { t } = useSession();
  const [expanded, setExpanded] = useState(false);
  const main = markets.filter((m) => m.risk_level !== null && !m.stale);
  const more = markets.filter((m) => m.risk_level === null || m.stale);
  const shown = expanded ? [...main, ...more] : main;

  return (
    <Surface>
      {shown.map((m, i) => {
        const leadText =
          isPredictive(mode) && m.lead_days !== null && m.lead_days > 0 && m.risk_level !== 'glut'
            ? t('glut_in_days', { days: m.lead_days })
            : null;
        const parts: string[] = [m.risk_level ? t(`risk_${m.risk_level}`) : t('risk_not_reported')];
        if (m.risk_level !== null) {
          if (m.arrival_ratio !== null) parts.push(t('ratio_usual', { ratio: m.arrival_ratio.toFixed(1) }));
          if (m.price_change_3d !== null) {
            parts.push(
              t('change_3d', { change: `${m.price_change_3d > 0 ? '+' : ''}${Math.round(m.price_change_3d * 100)}` }),
            );
          }
        }
        return (
          <ListRow key={m.market_id} first={i === 0} style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
            <RiskDot level={m.risk_level} />
            <View style={{ flex: 1, gap: 2 }}>
              <T bold size={SIZE.base}>
                {m.name}
                {m.distance_km !== null && (
                  <T size={SIZE.label} color={C.muted} style={{ fontWeight: 'normal' }}>
                    {'  '}
                    {t('km_value', { v: fmtNum(m.distance_km) })}
                    {m.distance_approx ? ` (${t('approx')})` : ''}
                  </T>
                )}
              </T>
              <T size={SIZE.label} color={C.muted}>
                {parts.join(' · ')}
              </T>
              {leadText && (
                <T bold size={SIZE.label}>
                  {leadText}
                </T>
              )}
              {m.stale && m.as_of_date && (
                <T bold size={SIZE.label} color={C.warnText} style={{ backgroundColor: C.warnBg, paddingHorizontal: 6, borderRadius: 6, alignSelf: 'flex-start' }}>
                  {t('as_of', { date: m.as_of_date })} · {t('stale')}
                </T>
              )}
            </View>
            {m.modal_price_rs_per_kg !== null && (
              <T bold>
                Rs {fmtRs(m.modal_price_rs_per_kg)}
                <T size={SIZE.label} color={C.muted}>
                  {' '}
                  /kg
                </T>
              </T>
            )}
          </ListRow>
        );
      })}
      {more.length > 0 && !expanded && (
        <Pressable accessibilityRole="button" onPress={() => setExpanded(true)}>
          <ListRow first={shown.length === 0} style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
            <T color={C.primary} bold style={{ flexShrink: 1 }}>
              {t('more_markets', { n: more.length })}
            </T>
            <Icon name="chevron" size={20} color={C.muted} />
          </ListRow>
        </Pressable>
      )}
    </Surface>
  );
}
