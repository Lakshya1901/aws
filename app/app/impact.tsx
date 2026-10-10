// Impact: "Since you started" (lifetime totals on this phone, lib/ledger.ts) and "Today's plan" (GET /impact).
import { router, useFocusEffect } from 'expo-router';
import { Pressable, View } from 'react-native';
import { useCallback, useEffect, useState } from 'react';
import { api } from '../api/client';
import type { ImpactResponse } from '../api/types';
import { ImpactHeadline, ImpactRows } from '../components/ImpactRows';
import { Lifetime } from '../components/Lifetime';
import { Banner, Btn, DataBanners, Loading, Screen, SectionTitle, T, useErrorText } from '../components/ui';
import { readLedger, totals, type LedgerTotals } from '../lib/ledger';
import { useSession } from '../lib/session';
import { C, RADIUS, SIZE } from '../lib/theme';

export default function ImpactScreen() {
  const { t, planId } = useSession();
  const errorText = useErrorText();
  const [data, setData] = useState<ImpactResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<'all' | 'today'>('all');
  const [life, setLife] = useState<LedgerTotals | null>(null);

  useFocusEffect(
    useCallback(() => {
      void readLedger().then((e) => setLife(totals(e)));
    }, []),
  );

  const load = useCallback(async () => {
    if (!planId) return;
    setLoading(true);
    setError(null);
    try {
      setData(await api.impact(planId));
    } catch (e) {
      setError(errorText(e));
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [planId]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <Screen nav>
      <View accessibilityRole="tablist" style={{ flexDirection: 'row', borderWidth: 1, borderColor: C.outline, borderRadius: RADIUS.pill, overflow: 'hidden' }}>
        {(['all', 'today'] as const).map((k, i) => (
          <Pressable
            key={k}
            accessibilityRole="tab"
            accessibilityState={{ selected: tab === k }}
            onPress={() => setTab(k)}
            style={{ flex: 1, minHeight: SIZE.touch, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 8, backgroundColor: tab === k ? C.tonal : 'transparent', borderLeftWidth: i ? 1 : 0, borderLeftColor: C.outline }}
          >
            <T bold={tab === k} color={tab === k ? C.onTonal : C.text} style={{ textAlign: 'center' }}>
              {k === 'all' ? t('since_start') : t('todays_plan')}
            </T>
          </Pressable>
        ))}
      </View>
      {tab === 'all' && life && <Lifetime totals={life} />}
      {tab === 'today' && !planId && (
        <>
          <T size={SIZE.large}>{t('no_plan')}</T>
          <Btn label={t('new_load')} onPress={() => router.push('/new-load')} />
        </>
      )}
      {tab === 'today' && loading && <Loading />}
      {tab === 'today' && error && (
        <>
          <Banner kind="error" text={error} />
          <Btn kind="secondary" label={t('retry')} onPress={() => void load()} />
        </>
      )}
      {tab === 'today' && data && !loading && (
        <>
          <DataBanners fixture={data._fixture} />
          <ImpactHeadline impact={data} />
          <SectionTitle>{t('impact_from')}</SectionTitle>
          <ImpactRows impact={data} lines="from" />
          <SectionTitle>{t('trip_costs')}</SectionTitle>
          <ImpactRows impact={data} lines="trip" />
        </>
      )}
    </Screen>
  );
}
