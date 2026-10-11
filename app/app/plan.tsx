// Loads (tab "Today's loads"): add a new load on top, then today's loads (POST /plan with every load used this
// session, plus unsold lots saved in the same plan), then the loads saved on this phone on earlier days
// (lib/ledger.ts), filterable. Each saved load can be ticked as sold.
import { router, useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Pressable, View } from 'react-native';
import { api } from '../api/client';
import type { PlanResponse } from '../api/types';
import { Icon } from '../components/Icon';
import { useOutletLabels } from '../components/RecommendationCard';
import { Banner, Btn, Chip, DataBanners, ListRow, Loading, Screen, SectionTitle, Surface, T, Tag, fmtDate, s, useErrorText } from '../components/ui';
import { fmtNum } from '../i18n';
import { readLedger, setSold, type LedgerEntry } from '../lib/ledger';
import { useSession } from '../lib/session';
import { C, SIZE } from '../lib/theme';
import { ImpactRows } from '../components/ImpactRows';

type Status = 'all' | 'not_sold' | 'sold';

export default function PlanScreen() {
  const { t, lang, loads, planId, setPlanId, cropLabel, demoBusy } = useSession();
  const L = useOutletLabels();
  const errorText = useErrorText();
  const [data, setData] = useState<PlanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [entries, setEntries] = useState<LedgerEntry[]>([]);
  const [status, setStatus] = useState<Status>('all');
  const [cropFilter, setCropFilter] = useState<string | null>(null);

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

  useFocusEffect(
    useCallback(() => {
      void readLedger().then(setEntries);
    }, [demoBusy, planId]),
  );

  const toggle = (e: LedgerEntry) => void setSold(e.key, !e.sold).then(setEntries);

  // Today = saved in the current plan; previous = everything else, newest day first.
  const inPlan = (e: LedgerEntry) => planId !== null && e.key.startsWith(`${planId}|`);
  const today = entries.filter(inPlan);
  const earlier = entries.filter((e) => !inPlan(e)).sort((a, b) => b.at.localeCompare(a.at));
  const crops = useMemo(() => [...new Set(earlier.map((e) => e.crop).filter((c): c is string => !!c))], [earlier]);
  const shown = earlier.filter(
    (e) => (status === 'all' || (status === 'sold') === !!e.sold) && (!cropFilter || e.crop === cropFilter),
  );
  const days = [...new Set(shown.map((e) => e.at.slice(0, 10)))];

  // Where a farm load of today's plan went, for entries saved before the outlet was stored.
  const allocOutlet = (e: LedgerEntry) => {
    const a = data?.allocations.find((x) => `${planId}|${x.load_id}` === e.key);
    return a ? (a.outlet.type === 'hold' ? t('hold_title') : L.name(a.outlet)) : null;
  };

  const row = (e: LedgerEntry, i: number) => {
    const where = e.outlet ?? allocOutlet(e);
    const money = e.extra_rs && e.extra_rs.mid > 0 ? e.extra_rs.mid : null;
    const fg = e.sold ? C.muted : C.text;
    return (
      <ListRow key={e.key} first={i === 0} style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
        <Pressable
          accessibilityRole="checkbox"
          accessibilityState={{ checked: !!e.sold }}
          accessibilityLabel={e.sold ? t('sold') : t('not_sold')}
          onPress={() => toggle(e)}
          hitSlop={8}
          style={{
            width: 32,
            height: 32,
            borderRadius: 16,
            borderWidth: 2,
            borderColor: e.sold ? C.primary : C.outline,
            backgroundColor: e.sold ? C.primary : 'transparent',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {e.sold ? <Icon name="check" size={18} color={C.primaryText} strokeWidth={2.8} /> : null}
        </Pressable>
        <View style={{ flex: 1, flexShrink: 1, gap: 2 }}>
          <T bold color={fg}>
            {`${t('kg_value', { v: fmtNum(e.qty_kg) })}${e.crop ? ` · ${cropLabel(e.crop)}` : ''}`}
          </T>
          {where ? (
            <T size={SIZE.small} color={C.muted}>
              {t('send_to', { outlet: where })}
            </T>
          ) : null}
          <View style={[s.row, { alignItems: 'center' }]}>
            {e.kind === 'rescue' ? <Tag text={t('rescued')} /> : null}
            {e.sold ? <Tag text={t('sold')} /> : null}
          </View>
        </View>
        {money !== null ? (
          <T bold color={fg}>{`Rs ${fmtNum(Math.round(money))}`}</T>
        ) : null}
      </ListRow>
    );
  };

  const totalKg = data ? data.allocations.reduce((a, x) => a + x.quantity_kg, 0) : 0;
  const addedTotal = data ? data.markets.reduce((a, m) => a + Math.max(0, m.added_kg), 0) : 0;
  const loadsIn = (marketId: string) =>
    data ? data.allocations.filter((a) => a.outlet.outlet_id === marketId).length : 0;

  return (
    <Screen nav>
      <Btn icon="plus" label={t('new_load')} onPress={() => router.push('/new-load')} />

      <SectionTitle>{t('todays_plan')}</SectionTitle>
      {demoBusy && <Loading />}
      {!demoBusy && loads.length === 0 && today.length === 0 && <T color={C.muted}>{t('plan_empty')}</T>}
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
        </>
      )}
      {!demoBusy && today.length > 0 && <Surface>{today.map(row)}</Surface>}
      {data && !loading && (
        <>
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
        </>
      )}

      <SectionTitle>{t('previous_loads')}</SectionTitle>
      {earlier.length === 0 ? (
        <T color={C.muted}>{t('no_previous')}</T>
      ) : (
        <>
          <View style={s.row}>
            {(['all', 'not_sold', 'sold'] as const).map((k) => (
              <Chip key={k} label={t(k === 'all' ? 'all_loads' : k)} selected={status === k} onPress={() => setStatus(k)} />
            ))}
          </View>
          {crops.length > 1 && (
            <View style={s.row}>
              <Chip label={t('all_loads')} selected={cropFilter === null} onPress={() => setCropFilter(null)} />
              {crops.map((c) => (
                <Chip key={c} label={cropLabel(c)} selected={cropFilter === c} onPress={() => setCropFilter(c)} />
              ))}
            </View>
          )}
          {days.map((d) => (
            <View key={d} style={{ gap: 8 }}>
              <T size={SIZE.label} color={C.muted}>
                {fmtDate(d)}
              </T>
              <Surface>{shown.filter((e) => e.at.slice(0, 10) === d).map(row)}</Surface>
            </View>
          ))}
        </>
      )}
    </Screen>
  );
}
