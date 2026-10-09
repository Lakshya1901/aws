// The recommendation card (Section 14.3): waste avoided first, redirected separately, extra distance + diesel,
// then earnings with the default market for comparison. Every figure carries a range or "(estimate)".
// The reason line cites an arrival multiple only when it drives the default's risk (D10); otherwise it shows the
// API explanation, which cites the price drop and the net-value gap.
import { View } from 'react-native';
import type { OutletOption, RecommendRequest, RecommendResponse } from '../api/types';
import { fmtNum, fmtRs } from '../i18n';
import { ratioDriven } from '../lib/recommend';
import { useSession } from '../lib/session';
import { C, SIZE } from '../lib/theme';
import { useWasteText } from './ImpactRows';
import { Banner, Btn, RiskBadge, T, s } from './ui';

export function useOutletLabels() {
  const { t } = useSession();
  return {
    typeLabel: (o: OutletOption) => t(`type_${o.type}`),
    /** Hold and the compost fallback have no name. */
    name: (o: OutletOption) => o.name ?? t(`type_${o.type}`),
    /** Stable key and "Use this" identity; hold/fallback have outlet_id null. */
    key: (o: OutletOption) => o.outlet_id ?? `_${o.type}`,
    km: (o: OutletOption) =>
      o.distance_km == null
        ? t('not_estimated')
        : `${t('km_value', { v: fmtNum(o.distance_km) })}${o.distance_approx ? ` (${t('approx')})` : ''}`,
    earn: (o: OutletOption) =>
      o.net_rs_per_kg == null
        ? t('not_estimated')
        : t('earn_value', { low: fmtRs(o.net_rs_per_kg.low), high: fmtRs(o.net_rs_per_kg.high) }),
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
  const wasteText = useWasteText();
  const { top, impact } = res;
  const dflt = res.default;
  const diverted = L.key(dflt) !== L.key(top);
  const hold = top.type === 'hold';
  const secondLife = top.type !== 'mandi' && !hold;
  const est = `(${t('estimate')})`;
  const cropName = t(`crop_${req.crop}`);

  const waste = wasteText(impact.waste_avoided_kg, 'load');
  const diesel =
    impact.diesel_l == null
      ? `${t('diesel')}: ${t('not_estimated')}`
      : impact.diesel_l < 0
        ? `${t('diesel_saved_value', { l: fmtNum(-impact.diesel_l, 1) })} ${est}`
        : `${t('diesel_value', { l: fmtNum(impact.diesel_l, 1) })} ${est}`;
  const extraKm =
    impact.extra_km == null
      ? t('not_estimated')
      : `${
          impact.extra_km < 0
            ? t('shorter_km_value', { km: fmtNum(-impact.extra_km) })
            : t('extra_km_value', { km: fmtNum(impact.extra_km) })
        }${top.distance_approx ? ` (${t('approx')})` : ''}`;
  // D10: the arrival multiple only when it drives the default's watch/glut level; else the API's explanation.
  const glutReason =
    diverted && ratioDriven(dflt) && dflt.arrival_ratio != null
      ? t('glut_reason', { market: L.name(dflt), ratio: dflt.arrival_ratio.toFixed(1), crop: cropName })
      : null;
  const explanation = res.explanation.text ? res.explanation.text : null;

  return (
    <View style={[s.card, { gap: 10 }]}>
      {secondLife && (
        <View style={{ gap: 4 }}>
          <Banner kind="info" text={t('second_life_title')} />
          <T bold>{t('second_life_body', { type: L.typeLabel(top) })}</T>
        </View>
      )}

      {hold && (
        <View style={{ gap: 4 }}>
          <Banner kind="info" text={t('second_life_title')} />
          <T bold>{t('hold_body')}</T>
        </View>
      )}

      <T bold size={SIZE.title}>
        {hold ? t('hold_title') : t('send_to', { outlet: L.name(top) })}
      </T>
      <T bold size={SIZE.large}>
        {t('load_line', { qty: fmtNum(req.quantity_kg), crop: cropName })}
      </T>
      <View style={s.row}>
        {top.type === 'mandi' ? <RiskBadge level={top.risk_level} /> : hold ? null : <T bold>{L.typeLabel(top)}</T>}
        {top.partnered === false && <Banner kind="warn" text={t('not_partnered')} />}
      </View>

      {glutReason ? <T bold>{glutReason}</T> : null}
      {!glutReason && diverted && explanation ? (
        <View style={{ gap: 2 }}>
          <T bold>{explanation}</T>
          {res.explanation.source === 'template' && <T color={C.muted}>{t('template_text')}</T>}
        </View>
      ) : null}

      <Row label={t('waste_avoided')} value={waste.value} sub={waste.sub} />
      <Row
        label={t('redirected')}
        value={t('kg_value', { v: fmtNum(impact.redirected_kg) })}
        sub={impact.redirected_kg > 0 ? t('redirected_value', { qty: fmtNum(impact.redirected_kg) }) : undefined}
      />
      <Row label={t('extra_km')} value={extraKm} sub={diesel} />
      <Row
        label={t('earnings')}
        value={top.net_rs_per_kg == null ? L.earn(top) : `${L.earn(top)} ${est}`}
        sub={
          diverted && dflt.net_rs_per_kg
            ? t('default_compare', {
                market: L.name(dflt),
                low: fmtRs(dflt.net_rs_per_kg.low),
                high: fmtRs(dflt.net_rs_per_kg.high),
              })
            : undefined
        }
      />

      {explanation && (glutReason || !diverted) ? (
        <View style={{ gap: 2 }}>
          <T>{res.explanation.text}</T>
          {res.explanation.source === 'template' && <T color={C.muted}>{t('template_text')}</T>}
        </View>
      ) : null}
      <T color={C.muted}>{t('spoilage_note')}</T>

      <View style={{ gap: 8 }}>
        {diverted && <Btn kind="secondary" label={t('why_not', { market: L.name(dflt) })} onPress={onWhyNot} />}
        {onListen && <Btn kind="secondary" label={t('listen')} onPress={onListen} />}
        {onListen && listenNote ? <T color={C.muted}>{listenNote}</T> : null}
        <Btn label={used ? t('accepted') : t('use_this')} onPress={onUse} disabled={used} />
      </View>
    </View>
  );
}
