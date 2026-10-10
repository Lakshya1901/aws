// The recommendation card (Section 14.3): waste avoided first, redirected separately, extra distance + diesel,
// then earnings with the default market for comparison. Every figure carries a range or "(estimate)".
// The reason line cites an arrival multiple only when it drives the default's risk (D10); otherwise it shows the
// API explanation, which cites the price drop and the net-value gap.
import { View } from 'react-native';
import type { OutletOption, RecommendRequest, RecommendResponse } from '../api/types';
import { fmtNum, fmtRs } from '../i18n';
import { ratioDriven } from '../lib/recommend';
import { useSession } from '../lib/session';
import { C, RADIUS, SIZE } from '../lib/theme';
import { useWasteText } from './ImpactRows';
import { Banner, Btn, RiskBadge, ListRow, Surface, Tag, T } from './ui';

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

function Row({ label, value, sub, first }: { label: string; value: string; sub?: string; first?: boolean }) {
  return (
    <ListRow first={first}>
      <T size={SIZE.small} color={C.muted}>
        {label}
      </T>
      <T bold size={SIZE.large}>
        {value}
      </T>
      {sub ? (
        <T size={SIZE.label} color={C.muted}>
          {sub}
        </T>
      ) : null}
    </ListRow>
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
  const reasonText = glutReason ?? explanation;
  const showTemplate = !glutReason && res.explanation.source === 'template';

  // "Rs a-b" large, the "per kg" remainder of earn_value muted under it.
  const perKg = (o: OutletOption) => {
    if (!o.net_rs_per_kg) return null;
    const range = t('rs_range', { low: fmtRs(o.net_rs_per_kg.low), high: fmtRs(o.net_rs_per_kg.high) });
    return { range, unit: L.earn(o).replace(range, '').trim() };
  };
  const earnBox = (o: OutletOption, recommended: boolean) => {
    const e = perKg(o);
    return (
      <View
        key={recommended ? 'top' : 'default'}
        style={{
          flex: 1,
          backgroundColor: C.surface,
          borderRadius: RADIUS.surface,
          padding: 14,
          gap: 4,
          borderWidth: recommended ? 2 : 0,
          borderColor: C.primary,
        }}
      >
        <T bold size={SIZE.small} color={recommended ? C.primary : C.muted}>
          {L.name(o)}
        </T>
        <T bold size={e ? SIZE.number : SIZE.large} color={recommended ? C.text : C.muted}>
          {e ? e.range : L.earn(o)}
        </T>
        {e?.unit ? (
          <T size={SIZE.label} color={C.muted}>
            {e.unit}
          </T>
        ) : null}
      </View>
    );
  };
  const showPair = diverted && !!dflt.net_rs_per_kg;

  return (
    <View style={{ gap: 16 }}>
      <View style={{ gap: 10 }}>
        <T bold size={SIZE.title}>
          {hold ? t('hold_title') : t('send_to', { outlet: L.name(top) })}
        </T>
        {!hold && (
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: 8 }}>
            {top.type === 'mandi' ? <RiskBadge level={top.risk_level} /> : <T bold>{L.typeLabel(top)}</T>}
            {top.partnered === false && <Tag dashed text={t('not_partnered')} />}
            {top.distance_km != null && (
              <T size={SIZE.small} color={C.muted}>
                {t('km_away', { v: fmtNum(top.distance_km) })}
                {top.distance_approx ? ` (${t('approx')})` : ''}
              </T>
            )}
          </View>
        )}
        {(secondLife || hold) && <Banner kind="info" text={`${t('second_life_title')}. ${hold ? t('hold_body') : t('second_life_body', { type: L.typeLabel(top) })}`} />}
        {reasonText ? (
          <View style={{ gap: 2 }}>
            <T size={17}>{reasonText}</T>
            {showTemplate && (
              <T size={SIZE.label} color={C.muted}>
                {t('template_text')}
              </T>
            )}
          </View>
        ) : null}
      </View>

      <View style={{ gap: 8 }}>
        <T bold size={SIZE.section}>
          {t('earnings')}
        </T>
        {showPair ? (
          <View style={{ flexDirection: 'row', gap: 12 }}>
            {earnBox(top, true)}
            {earnBox(dflt, false)}
          </View>
        ) : (
          <View style={{ flexDirection: 'row' }}>{earnBox(top, true)}</View>
        )}
        <T size={SIZE.label} color={C.muted}>
          {t('after_costs')}
        </T>
      </View>

      <Surface>
        <Row first label={t('waste_avoided')} value={waste.value} sub={waste.sub} />
        <Row
          label={t('redirected')}
          value={t('kg_value', { v: fmtNum(impact.redirected_kg) })}
          sub={impact.redirected_kg > 0 ? t('redirected_value', { qty: fmtNum(impact.redirected_kg) }) : undefined}
        />
        <Row label={t('extra_km')} value={extraKm} sub={diesel} />
      </Surface>

      <View style={{ gap: 12 }}>
        <Btn label={used ? t('accepted') : t('use_this')} onPress={onUse} disabled={used} />
        <View style={{ flexDirection: 'row', gap: 12 }}>
          {diverted && (
            <Btn kind="secondary" label={t('why_not', { market: L.name(dflt) })} onPress={onWhyNot} style={{ flex: 1 }} />
          )}
          {onListen && <Btn kind="secondary" icon="speaker" label={t('listen')} onPress={onListen} style={{ flex: 1 }} />}
        </View>
        {onListen && listenNote ? <T size={SIZE.label} color={C.muted}>{listenNote}</T> : null}
        <T size={SIZE.label} color={C.muted} style={{ textAlign: 'center' }}>
          {t('advice_note')}
        </T>
      </View>

      <T size={SIZE.label} color={C.muted}>
        {t('spoilage_note')}
      </T>
    </View>
  );
}
