// "Why not <default>?": before/after of the default market vs the recommendation for the same load.
import { Modal, ScrollView, View } from 'react-native';
import type { OutletOption } from '../api/types';
import { fmtNum } from '../i18n';
import { useSession } from '../lib/session';
import { C, SIZE } from '../lib/theme';
import { useOutletLabels } from './RecommendationCard';
import { Btn, RiskBadge, T, s } from './ui';

export function CompareSheet({
  visible,
  onClose,
  dflt,
  top,
  quantityKg,
  onUseDefault,
}: {
  onUseDefault: () => void; // override: send to the default market anyway (logged as an override)
  visible: boolean;
  onClose: () => void;
  dflt: OutletOption;
  top: OutletOption;
  quantityKg: number;
}) {
  const { t } = useSession();
  const L = useOutletLabels();
  const est = `(${t('estimate')})`;

  const cell = (o: OutletOption, row: string) => {
    switch (row) {
      case 'risk':
        return o.type === 'mandi' ? <RiskBadge level={o.risk_level} /> : <T bold>{L.typeLabel(o)}</T>;
      case 'ratio':
        return <T bold>{o.arrival_ratio != null ? `${o.arrival_ratio.toFixed(1)}x` : t('not_estimated')}</T>;
      case 'distance':
        return <T bold>{L.km(o)}</T>;
      case 'spoilage':
        return (
          <T bold>
            {o.spoilage_share != null ? `${Math.round(o.spoilage_share * 100)}% ${est}` : t('not_estimated')}
          </T>
        );
      case 'earn_kg':
        return (
          <T bold size={SIZE.large}>
            {L.earn(o)}
          </T>
        );
      default:
        return (
          <T bold size={SIZE.large}>
            {o.net_rs_per_kg
              ? `${t('rs_range', {
                  low: fmtNum(o.net_rs_per_kg.low * quantityKg),
                  high: fmtNum(o.net_rs_per_kg.high * quantityKg),
                })} ${est}`
              : t('not_estimated')}
          </T>
        );
    }
  };

  const rows: [string, string][] = [
    ['risk', t('row_risk')],
    ['ratio', t('row_ratio')],
    ['distance', t('row_distance')],
    ['spoilage', t('row_spoilage')],
    ['earn_kg', t('row_earn_kg')],
    ['earn_load', t('row_earn_load')],
  ];

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose} transparent>
      <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' }}>
        <View style={{ backgroundColor: C.bg, borderTopLeftRadius: 16, borderTopRightRadius: 16, maxHeight: '90%' }}>
          <ScrollView contentContainerStyle={{ padding: 16, gap: 12 }}>
            <T bold size={SIZE.title}>
              {t('compare_title', { default: L.name(dflt), top: L.name(top) })}
            </T>
            <T>{t('load_line', { qty: fmtNum(quantityKg), crop: '' }).trim()}</T>
            <View style={{ flexDirection: 'row', gap: 8 }}>
              <View style={{ flex: 1 }} />
              <View style={{ flex: 1 }}>
                <T bold>{t('col_default')}</T>
                <T>{L.name(dflt)}</T>
              </View>
              <View style={{ flex: 1 }}>
                <T bold color={C.primary}>
                  {t('col_recommended')}
                </T>
                <T>{L.name(top)}</T>
              </View>
            </View>
            {rows.map(([key, label]) => (
              <View key={key} style={[s.card, { flexDirection: 'row', gap: 8, padding: 10 }]}>
                <View style={{ flex: 1 }}>
                  <T color={C.muted}>{label}</T>
                </View>
                <View style={{ flex: 1 }}>{cell(dflt, key)}</View>
                <View style={{ flex: 1 }}>{cell(top, key)}</View>
              </View>
            ))}
            <Btn label={t('close')} onPress={onClose} />
            <Btn kind="secondary" label={`${t('send_here')}: ${L.name(dflt)}`} onPress={onUseDefault} />
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}
