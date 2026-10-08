// Today's plan: POST /plan with every load used this session (records "Use this" and overrides),
// then shows the allocation per load and the quantity added per market.
import { router } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { View } from 'react-native';
import { api } from '../api/client';
import type { PlanResponse } from '../api/types';
import { useOutletLabels } from '../components/RecommendationCard';
import { Banner, Btn, DataBanners, Loading, RiskBadge, Screen, T, s, useErrorText } from '../components/ui';
import { fmtNum } from '../i18n';
import { useSession } from '../lib/session';
import { C, SIZE } from '../lib/theme';
import { ImpactRows, useWasteText } from '../components/ImpactRows';

export default function PlanScreen() {
  const { t, lang, loads, planId, setPlanId } = useSession();
  const L = useOutletLabels();
  const wasteText = useWasteText();
  const errorText = useErrorText();
  const [data, setData] = useState<PlanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (loads.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.plan({ loads, language: lang ?? 'en', ...(planId ? { plan_id: planId } : {}) });
      setData(res);
      setPlanId(res.plan_id);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loads, lang, planId]);

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loads]);

  if (loads.length === 0) {
    return (
      <Screen>
        <T size={SIZE.large}>{t('plan_empty')}</T>
        <Btn label={t('new_load')} onPress={() => router.push('/new-load')} />
      </Screen>
    );
  }

  return (
    <Screen>
      {loading && <Loading />}
      {error && (
        <>
          <Banner kind="error" text={error} />
          <Btn kind="secondary" label={t('retry')} onPress={() => void load()} />
        </>
      )}
      {data && !loading && (
        <>
          <DataBanners
            fixture={data._fixture}
            replayDate={data.replay_date}
            stale={data.data.stale}
            demoLoads={data.demo_loads}
          />
          {data.allocations.map((a) => {
            const hold = a.outlet.type === 'hold';
            const waste = wasteText(a.impact.waste_avoided_kg, 'load');
            return (
              <View key={a.load_id} style={s.card}>
                <T bold size={SIZE.large}>
                  {t('load_line', { qty: fmtNum(a.quantity_kg), crop: t(`crop_${a.crop}`) })}
                </T>
                <T bold size={SIZE.number}>
                  {hold ? t('hold_title') : t('send_to', { outlet: L.name(a.outlet) })}
                </T>
                <View style={s.row}>
                  {a.outlet.type === 'mandi' ? (
                    <RiskBadge level={a.outlet.risk_level} />
                  ) : (
                    <T bold>{L.typeLabel(a.outlet)}</T>
                  )}
                  {a.outlet.partnered === false && <Banner kind="warn" text={t('not_partnered')} />}
                </View>
                <T>{a.outlet.net_rs_per_kg ? `${L.earn(a.outlet)} (${t('estimate')})` : L.earn(a.outlet)}</T>
                {!hold && <T color={C.muted}>{L.km(a.outlet)}</T>}
                <T>{`${t('waste_avoided')}: ${waste.value}`}</T>
                {waste.sub ? <T color={C.muted}>{waste.sub}</T> : null}
              </View>
            );
          })}

          <T bold size={SIZE.title}>
            {t('added_per_market')}
          </T>
          {data.markets.map((m) => (
            <View key={m.market_id} style={[s.card, { flexDirection: 'row', justifyContent: 'space-between' }]}>
              <View style={{ flexShrink: 1, gap: 4 }}>
                <T bold size={SIZE.large}>
                  {m.name ?? m.market_id}
                </T>
                {m.capped && <Banner kind="warn" text={t('market_capped')} />}
              </View>
              <T bold size={SIZE.number}>
                {`+${t('kg_value', { v: fmtNum(m.added_kg) })}`}
              </T>
            </View>
          ))}

          <T bold size={SIZE.title}>
            {t('total_impact')}
          </T>
          <ImpactRows impact={data.impact} />
        </>
      )}
      <Btn kind="secondary" label={t('new_load')} onPress={() => router.push('/new-load')} />
      <Btn kind="secondary" label={t('impact')} onPress={() => router.push('/impact')} />
    </Screen>
  );
}
