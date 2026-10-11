// Today's plan: POST /plan with every load used this session (records "Use this" and overrides),
// then shows the allocation per load and the quantity added per market.
import { router } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { View } from 'react-native';
import { api } from '../api/client';
import type { PlanResponse } from '../api/types';
import { useOutletLabels } from '../components/RecommendationCard';
import { Banner, Btn, DataBanners, ListRow, Loading, RiskDot, Screen, SectionTitle, Surface, T, Tag, useErrorText } from '../components/ui';
import { fmtNum } from '../i18n';
import { useSession } from '../lib/session';
import { C, SIZE } from '../lib/theme';
import { ImpactRows } from '../components/ImpactRows';

export default function PlanScreen() {
  const { t, lang, loads, planId, setPlanId, cropLabel, demoBusy } = useSession();
  const L = useOutletLabels();
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
    return demoBusy ? (
      <Screen nav>
        <Loading />
      </Screen>
    ) : (
      <Screen nav>
        <T size={SIZE.large}>{t('plan_empty')}</T>
        <Btn label={t('new_load')} onPress={() => router.push('/new-load')} />
      </Screen>
    );
  }

  const totalKg = data ? data.allocations.reduce((a, x) => a + x.quantity_kg, 0) : 0;
  const addedTotal = data ? data.markets.reduce((a, m) => a + Math.max(0, m.added_kg), 0) : 0;
  const loadsIn = (marketId: string) =>
    data ? data.allocations.filter((a) => a.outlet.outlet_id === marketId).length : 0;

  return (
    <Screen nav>
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
            pricesDate={data.data.prices_date}
          />
          <View style={{ gap: 4 }}>
            <T bold size={SIZE.title}>
              {t('plan_headline', { n: String(data.allocations.length), kg: fmtNum(totalKg) })}
            </T>
            <T size={SIZE.small} color={C.muted}>
              {t('plan_spread')}
            </T>
          </View>

          <SectionTitle>{t('added_per_market')}</SectionTitle>
          <Surface style={{ paddingTop: 16 }}>
            {addedTotal > 0 && (
              <View
                style={{
                  height: 12,
                  borderRadius: 6,
                  backgroundColor: C.track,
                  overflow: 'hidden',
                  flexDirection: 'row',
                  marginHorizontal: 16,
                  marginBottom: 8,
                }}
              >
                {data.markets.map((m, i) =>
                  m.added_kg > 0 ? (
                    <View
                      key={m.market_id}
                      style={{ flex: m.added_kg, backgroundColor: i === 0 ? C.primary : i === 1 ? C.tonal : C.outline }}
                    />
                  ) : null,
                )}
              </View>
            )}
            {data.markets.map((m, i) => (
              <ListRow key={m.market_id} first={i === 0 && addedTotal === 0} style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
                <View style={{ flex: 1, flexShrink: 1, gap: 4 }}>
                  <T bold>{m.name ?? m.market_id}</T>
                  <T size={SIZE.small} color={C.muted}>
                    {loadsIn(m.market_id) === 1 ? t('load_one') : t('loads_count', { n: String(loadsIn(m.market_id)) })}
                  </T>
                  {m.capped && (
                    <View style={{ flexDirection: 'row' }}>
                      <Banner kind="warn" text={t('market_capped')} />
                    </View>
                  )}
                </View>
                <T bold size={SIZE.section}>
                  {`+${t('kg_value', { v: fmtNum(m.added_kg) })}`}
                </T>
              </ListRow>
            ))}
          </Surface>

          <SectionTitle>{t('total_impact')}</SectionTitle>
          <ImpactRows impact={data.impact} lines="plan" />

          <SectionTitle>{t('loads')}</SectionTitle>
          <Surface>
            {data.allocations.map((a, i) => {
              const hold = a.outlet.type === 'hold';
              return (
                <ListRow key={a.load_id} first={i === 0} style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
                  <View style={{ minWidth: 88 }}>
                    <T bold>{t('kg_value', { v: fmtNum(a.quantity_kg) })}</T>
                    <T size={SIZE.small} color={C.muted}>
                      {cropLabel(a.crop)}
                    </T>
                  </View>
                  <View style={{ flex: 1, flexShrink: 1, gap: 2 }}>
                    <T bold>{hold ? t('hold_title') : L.name(a.outlet)}</T>
                    <T size={SIZE.small} color={C.muted}>
                      {L.earn(a.outlet)}
                    </T>
                    {a.outlet.type !== 'mandi' ? <T size={SIZE.label}>{L.typeLabel(a.outlet)}</T> : null}
                    {a.outlet.partnered === false && (
                      <View style={{ flexDirection: 'row' }}>
                        <Tag text={t('not_partnered')} dashed />
                      </View>
                    )}
                  </View>
                  {a.outlet.type === 'mandi' ? <RiskDot level={a.outlet.risk_level} /> : null}
                </ListRow>
              );
            })}
          </Surface>
        </>
      )}
      {!loading && <Btn label={t('new_load')} onPress={() => router.push('/new-load')} />}
    </Screen>
  );
}
