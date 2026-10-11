// Impact, one page: lifetime totals on this phone (lib/ledger.ts) on top, today's plan (GET /impact) below.
import { useFocusEffect } from 'expo-router';
import { useCallback, useMemo, useState } from 'react';
import { api } from '../api/client';
import type { ImpactResponse } from '../api/types';
import { ImpactHeadline, ImpactRows } from '../components/ImpactRows';
import { Lifetime } from '../components/Lifetime';
import { Banner, Btn, DataBanners, Loading, Screen, SectionTitle, T, useErrorText } from '../components/ui';
import { readLedger, totals, type LedgerEntry } from '../lib/ledger';
import { useSession } from '../lib/session';
import { C } from '../lib/theme';

export default function ImpactScreen() {
  const { t, planId, demoBusy } = useSession();
  const errorText = useErrorText();
  const [data, setData] = useState<ImpactResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [entries, setEntries] = useState<LedgerEntry[] | null>(null);
  // Today's plan counts in the lifetime totals too (lib/ledger.ts totals).
  const life = useMemo(
    () => (entries ? totals(entries, planId && data?.plan_id === planId ? { id: planId, impact: data } : null) : null),
    [entries, data, planId],
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

  useFocusEffect(
    useCallback(() => {
      void readLedger().then(setEntries);
      void load();
    }, [load, demoBusy]),
  );

  return (
    <Screen nav>
      <SectionTitle>{t('since_start')}</SectionTitle>
      {demoBusy ? <Loading /> : life && <Lifetime totals={life} />}

      <SectionTitle>{t('todays_plan')}</SectionTitle>
      {!planId && <T color={C.muted}>{t('no_plan')}</T>}
      {loading && <Loading />}
      {error && (
        <>
          <Banner kind="error" text={error} />
          <Btn kind="secondary" label={t('retry')} onPress={() => void load()} />
        </>
      )}
      {data && !loading && (
        <>
          <DataBanners fixture={data._fixture} />
          <ImpactHeadline impact={data} />
          <ImpactRows impact={data} lines="trip" />
        </>
      )}
    </Screen>
  );
}
