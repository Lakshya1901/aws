// The recommendation card (Section 14.3): waste avoided first, redirected separately, extra distance + diesel,
// then earnings with the default market for comparison. Every figure carries a range or "(estimate)".
import { View } from 'react-native';
import type { OutletOption, RecommendRequest, RecommendResponse } from '../api/types';
import { fmtNum, fmtRs } from '../i18n';
import { useSession } from '../lib/session';
import { C, SIZE } from '../lib/theme';
import { Banner, Btn, RiskBadge, T, s } from './ui';

export function useOutletLabels() {
  const { t } = useSession();
  return {
    typeLabel: (o: OutletOption) => t(`type_${o.type}`),
    km: (o: OutletOption) =>
      o.distance_km == null
        ? t('not_estimated')
        : `${t('km_value', { v: fmtNum(o.distance_km) })}${o.distance_approx ? ` (${t('approx')})` : ''}`,
    earn: (o: OutletOption) =>
      t('earn_value', { low: fmtRs(o.net_rs_per_kg.low), high: fmtRs(o.net_rs_per_kg.high) }),
  };
}

function Row({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <View style={{ gap: 2, paddingVertical: 4 }}>
      <T color={C.muted}>{label}</T>
      <T bold size={SIZE.number}>
        {value}
      </T>
      {sub ? <T>{sub}</T> : null}
    </View>
  );
}

export function RecommendationCard({
  req,
  res,
  onWhyNot,
  onListen,
  listenNote,
  onUse,
  used,
}: {
  req: RecommendRequest;
  res: RecommendResponse;
  onWhyNot: () => void;
  onListen: (() => void) | null; // null hides Listen (e.g. /speak failed)
  listenNote: string | null;
  onUse: () => void;
  used: boolean;
}) {
  const { t } = useSession();
  const L = useOutletLabels();
  const { top, impact } = res;
  const dflt = res.default;
  const diverted = dflt.outlet_id !== top.outlet_id;
  const secondLife = top.type !== 'mandi';
  const est = `(${t('estimate')})`;
  const cropName = t(`crop_${req.crop}`);

  const waste = impact.waste_avoided_kg;
  const diesel =
    impact.diesel_l == null
      ? `${t('diesel')}: ${t('not_estimated')}`
      : `${t('diesel_value', { l: fmtNum(impact.diesel_l, 1) })} ${est}`;

  return (
    <View style={[s.card, { gap: 10 }]}>
      {secondLife && (
        <View style={{ gap: 4 }}>
          <Banner kind="info" text={t('second_life_title')} />
          <T bold>{t('second_life_body', { type: L.typeLabel(top) })}</T>
        </View>
      )}

      <T bold size={SIZE.title}>
        {t('send_to', { outlet: top.name })}
      </T>
      <T bold size={SIZE.large}>
        {t('load_line', { qty: fmtNum(req.quantity_kg), crop: cropName })}
      </T>
      <View style={s.row}>
        {top.type === 'mandi' ? <RiskBadge level={top.risk_level} /> : <T bold>{L.typeLabel(top)}</T>}
        {top.partnered === false && <Banner kind="warn" text={t('not_partnered')} />}
      </View>

      {diverted && dflt.arrival_ratio != null && (dflt.risk_level === 'glut' || dflt.risk_level === 'watch') && (
        <T bold>
          {t('glut_reason', { market: dflt.name, ratio: dflt.arrival_ratio.toFixed(1), crop: cropName })}
        </T>
      )}

      <Row
        label={t('waste_avoided')}
        value={waste ? t('waste_value', { mid: fmtNum(waste.mid) }) : t('not_estimated')}
        sub={waste ? `${t('waste_range', { low: fmtNum(waste.low), high: fmtNum(waste.high) })} ${est}` : undefined}
      />
      <Row
        label={t('redirected')}
        value={t('kg_value', { v: fmtNum(impact.redirected_kg) })}
        sub={impact.redirected_kg > 0 ? t('redirected_value', { qty: fmtNum(impact.redirected_kg) }) : undefined}
      />
      <Row
        label={t('extra_km')}
        value={
          impact.extra_km == null
            ? t('not_estimated')
            : `${t('extra_km_value', { km: fmtNum(impact.extra_km) })}${top.distance_approx ? ` (${t('approx')})` : ''}`
        }
        sub={diesel}
      />
      <Row
        label={t('earnings')}
        value={`${L.earn(top)} ${est}`}
        sub={
          diverted
            ? t('default_compare', {
                market: dflt.name,
                low: fmtRs(dflt.net_rs_per_kg.low),
                high: fmtRs(dflt.net_rs_per_kg.high),
              })
            : undefined
        }
      />

      {res.explanation.text ? (
        <View style={{ gap: 2 }}>
          <T>{res.explanation.text}</T>
          {res.explanation.source === 'template' && <T color={C.muted}>{t('template_text')}</T>}
        </View>
      ) : null}
      <T color={C.muted}>{t('spoilage_note')}</T>

      <View style={{ gap: 8 }}>
        {diverted && <Btn kind="secondary" label={t('why_not', { market: dflt.name })} onPress={onWhyNot} />}
        {onListen && <Btn kind="secondary" label={t('listen')} onPress={onListen} />}
        {onListen && listenNote ? <T color={C.muted}>{listenNote}</T> : null}
        <Btn label={used ? t('accepted') : t('use_this')} onPress={onUse} disabled={used} />
      </View>
    </View>
  );
}
